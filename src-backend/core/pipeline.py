"""
Audio Processing Pipeline
Coordinates VAD, ASR, and LLM correction/translation engines for real-time voice processing.
"""

import logging
import time
import numpy as np
from .vad_engine import VADEngine
from .asr_engine import ASREngine
from .llm_corrector import LLMCorrector
from .llm_translator import LLMTranslator
from .text_input import TextInput
from .config import Config
from .history_store import HistoryStore

logger = logging.getLogger(__name__)


class AudioPipeline:
    """Main audio processing pipeline."""

    def __init__(self, on_status=None):
        self.config = Config()
        self.vad = VADEngine()
        self.asr = ASREngine()
        self.llm = LLMCorrector() if self.config.llm_enabled else None
        self.translator = LLMTranslator() if self.config.llm_enabled else None
        self.text_input = TextInput()
        self.audio_buffer = bytearray()
        # Pre-buffer to capture audio before VAD detects speech (100ms at 16kHz, 16-bit = 3200 bytes)
        self._pre_buffer = bytearray()
        self._pre_buffer_size = 32 * 200  # 200ms * 16000Hz * 2 bytes
        self._speech_just_started = False
        self.is_initialized = False
        self._on_status = on_status
        # Runtime config (can be changed per session)
        self._correction_enabled = True
        self._target_language = None
        self._asr_language = None
        # Context-aware correction config
        self._context_enabled = True
        self._context_count = 3
        # History store for context
        self.history_store = HistoryStore()

    def set_config(self, correction_enabled: bool = True, target_language: str = None, asr_language: str = None, asr_model_path: str = None, context_enabled: bool = True, context_count: int = 3):
        """Set runtime configuration for correction and translation."""
        self._correction_enabled = correction_enabled
        self._target_language = target_language if target_language else None
        self._asr_language = asr_language if asr_language else None
        self._context_enabled = context_enabled
        self._context_count = context_count
        if asr_model_path:
            self.asr.set_model_path(asr_model_path)
        logger.info(f"Pipeline config: asr_language={asr_language}, correction={correction_enabled}, target_language={target_language}, context_enabled={context_enabled}, context_count={context_count}")

    def _emit_status(self, status: str, **kwargs):
        """Emit status update."""
        if self._on_status:
            self._on_status({"type": "status", "status": status, **kwargs})

    def _emit_partial(self, text: str):
        """Emit partial transcription result."""
        if self._on_status:
            self._on_status({"type": "transcription_partial", "text": text})

    def initialize(self) -> None:
        """Initialize all pipeline components."""
        if self.is_initialized:
            return
        self.vad.initialize()
        self.asr.initialize()
        if self.llm:
            self.llm.initialize()
        if self.translator:
            self.translator.initialize()
        self.text_input.initialize()
        self.history_store.initialize()
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

        # Track if speech just started (first frame of speech)
        speech_just_started = vad_result["is_speech"] and not self._speech_just_started

        if vad_result["is_speech"]:
            # If speech just started, prepend the pre-buffer to capture audio before VAD detection
            if speech_just_started:
                self.audio_buffer.extend(self._pre_buffer)
                self._speech_just_started = True
            self.audio_buffer.extend(audio_bytes)
            buffer_duration = len(self.audio_buffer) / 32000
            self._emit_status("speaking", buffer_duration=buffer_duration)
        else:
            # Maintain rolling pre-buffer when not in speech
            if not self._speech_just_started:
                self._pre_buffer.extend(audio_bytes)
                # Keep only the last 100ms
                if len(self._pre_buffer) > self._pre_buffer_size:
                    self._pre_buffer = self._pre_buffer[-self._pre_buffer_size:]

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
            self._pre_buffer.clear()
            self._speech_just_started = False
            self.vad.reset()

            # Step 1: ASR Transcription (streaming)
            self._emit_status("transcribing", audio_duration=audio_duration)
            t_asr_start = time.perf_counter()
            # Use configured language, 'auto' means let model detect
            asr_lang = None if self._asr_language == 'auto' else self._asr_language
            transcription = self.asr.transcribe_stream(
                audio_float32,
                language=asr_lang,
                on_partial=self._emit_partial
            )
            t_asr_end = time.perf_counter()
            logger.info(f"[TIMING] ASR completed in {(t_asr_end - t_asr_start)*1000:.0f}ms, text='{transcription}'")

            if transcription:
                # Emit transcription result
                transcription_result = {
                    "type": "transcription",
                    "text": transcription,
                    "is_final": False,  # Not final until all processing completes
                    "audio_duration": round(audio_duration, 2),
                }

                current_text = transcription
                original_text = transcription

                # Send intermediate transcription result immediately
                if self._on_status:
                    self._on_status(transcription_result)

                # Step 2: LLM Correction (if enabled)
                if self._correction_enabled and self.llm and self.llm.enabled:

                    self._emit_status("correcting", original_text=transcription)
                    t_llm_start = time.perf_counter()
                    # Use configured ASR language for correction context
                    correction_lang = self._asr_language if self._asr_language and self._asr_language != 'auto' else self.asr.default_language

                    # Get context from history if enabled
                    context = None
                    if self._context_enabled and self._context_count > 0:
                        context = self.history_store.get_recent(self._context_count)

                    correction_result = self.llm.correct(
                        transcription,
                        language=correction_lang,
                        context=context
                    )
                    t_llm_end = time.perf_counter()
                    logger.info(f"[TIMING] LLM correction completed in {(t_llm_end - t_llm_start)*1000:.0f}ms")

                    current_text = correction_result.get("corrected_text", transcription)

                # Step 3: LLM Translation (if target language specified)
                if self._target_language and self.translator:
                    self._emit_status("translating", text=current_text)
                    t_trans_start = time.perf_counter()
                    translation_result = self.translator.translate(
                        current_text,
                        self._target_language
                    )
                    t_trans_end = time.perf_counter()
                    logger.info(f"[TIMING] LLM translation completed in {(t_trans_end - t_trans_start)*1000:.0f}ms")

                    current_text = translation_result.get("translated_text", current_text)

                # Build final result
                result = {
                    "type": "correction",
                    "text": current_text,
                    "original_text": original_text,
                    "is_corrected": current_text != original_text,
                    "is_final": True,
                }

                # Step 4: Input text at cursor position
                self._emit_status("inputting", text=current_text)
                self.text_input.input_text_typewriter(current_text)

                # Step 5: Save to history for future context
                self.history_store.add(
                    text=current_text,
                    original=original_text,
                    duration=audio_duration,
                    language=correction_lang if self._correction_enabled else (self._asr_language or 'zh')
                )

            t_end = time.perf_counter()
            logger.info(f"[TIMING] Total processing time: {(t_end - t_start)*1000:.0f}ms")
            self._emit_status("recording")

        return result

    def reset(self) -> None:
        """Reset pipeline state."""
        self.audio_buffer.clear()
        self._pre_buffer.clear()
        self._speech_just_started = False
        self.vad.reset()

    def update_llm_config(self, config: dict) -> None:
        """Update LLM configuration dynamically."""
        if self.llm:
            self.llm.reconfigure(**config)
        if self.translator:
            self.translator.reconfigure(**config)
        logger.info(f"LLM config updated: {config}")
