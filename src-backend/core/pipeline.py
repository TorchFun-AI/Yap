"""
Audio Processing Pipeline
Coordinates VAD, ASR, and LLM correction engines for real-time voice processing.
"""

import logging
import time
import numpy as np
from .vad_engine import VADEngine
from .asr_engine import ASREngine
from .llm_corrector import LLMCorrector
from .config import Config

logger = logging.getLogger(__name__)


class AudioPipeline:
    """Main audio processing pipeline."""

    def __init__(self, on_status=None):
        self.config = Config()
        self.vad = VADEngine()
        self.asr = ASREngine()
        self.llm = LLMCorrector() if self.config.llm_enabled else None
        self.audio_buffer = bytearray()
        self.is_initialized = False
        self._on_status = on_status

    def _emit_status(self, status: str, **kwargs):
        """Emit status update."""
        if self._on_status:
            self._on_status({"type": "status", "status": status, **kwargs})

    def initialize(self) -> None:
        """Initialize all pipeline components."""
        if self.is_initialized:
            return
        self.vad.initialize()
        self.asr.initialize()
        if self.llm:
            self.llm.initialize()
        self.is_initialized = True
        logger.info("Pipeline initialized")

    def process_chunk(self, audio_bytes: bytes) -> dict:
        """
        Process audio chunk through VAD and ASR.

        Args:
            audio_bytes: Raw PCM16 audio bytes

        Returns:
            Processing result dict
        """
        if not self.is_initialized:
            self.initialize()

        vad_result = self.vad.process_chunk(audio_bytes)

        if vad_result["is_speech"]:
            self.audio_buffer.extend(audio_bytes)
            buffer_duration = len(self.audio_buffer) / 32000
            self._emit_status("speaking", buffer_duration=buffer_duration)

        result = {
            "type": "vad",
            "is_speech": vad_result["is_speech"],
            "confidence": vad_result["confidence"],
            "buffer_duration": len(self.audio_buffer) / 32000,
        }

        if vad_result["speech_ended"] and len(self.audio_buffer) > 0:
            t_start = time.perf_counter()
            audio_duration = len(self.audio_buffer) / 32000
            logger.info(f"[TIMING] Speech ended, audio_duration={audio_duration:.2f}s")

            audio_int16 = np.frombuffer(bytes(self.audio_buffer), dtype=np.int16)
            audio_float32 = audio_int16.astype(np.float32) / 32768.0
            self.audio_buffer.clear()
            self.vad.reset()

            # Step 1: ASR Transcription
            self._emit_status("transcribing", audio_duration=audio_duration)
            t_asr_start = time.perf_counter()
            transcription = self.asr.transcribe(audio_float32)
            t_asr_end = time.perf_counter()
            logger.info(f"[TIMING] ASR completed in {(t_asr_end - t_asr_start)*1000:.0f}ms, text='{transcription}'")

            if transcription:
                # Emit transcription result
                result = {
                    "type": "transcription",
                    "text": transcription,
                    "is_final": False,  # Not final until correction completes
                }

                # Step 2: LLM Correction
                if self.llm and self.llm.enabled:
                    self._emit_status("correcting", original_text=transcription)
                    t_llm_start = time.perf_counter()
                    correction_result = self.llm.correct(
                        transcription,
                        language=self.asr.default_language
                    )
                    t_llm_end = time.perf_counter()
                    logger.info(f"[TIMING] LLM correction completed in {(t_llm_end - t_llm_start)*1000:.0f}ms")

                    result = {
                        "type": "correction",
                        "text": correction_result.get("corrected_text", transcription),
                        "original_text": transcription,
                        "is_corrected": correction_result.get("is_corrected", False),
                        "is_final": True,
                    }

                    if "error" in correction_result:
                        result["correction_error"] = correction_result["error"]
                else:
                    # LLM not available, transcription is final
                    result["is_final"] = True

            t_end = time.perf_counter()
            logger.info(f"[TIMING] Total processing time: {(t_end - t_start)*1000:.0f}ms")
            self._emit_status("recording")

        return result

    def reset(self) -> None:
        """Reset pipeline state."""
        self.audio_buffer.clear()
        self.vad.reset()
