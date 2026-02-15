"""
Audio Processing Pipeline
Coordinates VAD, ASR, and LLM correction/translation engines for real-time voice processing.
"""

import logging
import time
import numpy as np
from .vad_engine import VADEngine
from .asr_engine import ASREngine, StreamingASREngine
from .llm_corrector import LLMCorrector
from .llm_translator import LLMTranslator
from .config import Config
from .history_store import HistoryStore

logger = logging.getLogger(__name__)


class AudioPipeline:
    """Main audio processing pipeline."""

    # Idle timeout: auto-stop after 30s silence
    IDLE_TIMEOUT_SECONDS = 30

    def __init__(self, on_status=None):
        self.config = Config()
        self.vad = VADEngine()
        self.asr = ASREngine()
        self.llm = LLMCorrector() if self.config.llm_enabled else None
        self.translator = LLMTranslator() if self.config.llm_enabled else None
        self.audio_buffer = bytearray()
        # Pre-buffer to capture audio before VAD detects speech (100ms at 16kHz, 16-bit = 3200 bytes)
        self._pre_buffer = bytearray()
        self._pre_buffer_size = 32 * 300  # 300ms * 16000Hz * 2 bytes
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
        # Output mode config
        self._auto_input_mode = 'input'  # 'input', 'clipboard', 'none'
        # History store for context
        self.history_store = HistoryStore()
        # Streaming ASR engine for real-time transcription
        self._streaming_asr: StreamingASREngine = None
        # Idle timeout tracking
        self._last_speech_time: float = 0.0
        self._idle_timed_out = False

    def set_config(self, correction_enabled: bool = True, target_language: str = None, asr_language: str = None, asr_model_id: str = None, context_enabled: bool = True, context_count: int = 3, auto_input_mode: str = 'input'):
        """Set runtime configuration for correction and translation."""
        self._correction_enabled = correction_enabled
        self._target_language = target_language if target_language else None
        self._asr_language = asr_language if asr_language else None
        self._context_enabled = context_enabled
        self._context_count = context_count
        self._auto_input_mode = auto_input_mode if auto_input_mode else 'input'
        if asr_model_id:
            self.asr.set_model_id(asr_model_id)
        logger.info(f"Pipeline config: asr_language={asr_language}, correction={correction_enabled}, target_language={target_language}, context_enabled={context_enabled}, context_count={context_count}, auto_input_mode={auto_input_mode}")

    def _emit_status(self, status: str, **kwargs):
        """Emit status update."""
        if self._on_status:
            self._on_status({"type": "status", "status": status, **kwargs})

    def _emit_partial(self, text: str):
        """Emit partial transcription result."""
        logger.info(f"[STREAMING] _emit_partial called: {text[:30]}...")
        if self._on_status:
            self._on_status({"type": "transcription_partial", "text": text})

    def initialize(self) -> None:
        """Initialize all pipeline components."""
        if self.is_initialized:
            return
        self.vad.initialize()
        self.asr.set_on_status(self._on_status)
        self.asr.initialize()
        if self.llm:
            self.llm.initialize()
        if self.translator:
            self.translator.initialize()
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

        # Initialize idle timer on first chunk
        if self._last_speech_time == 0.0:
            self._last_speech_time = time.perf_counter()

        # Track if speech just started (first frame of speech)
        speech_just_started = vad_result["is_speech"] and not self._speech_just_started

        if vad_result["is_speech"]:
            # Reset idle tracking on any speech
            self._last_speech_time = time.perf_counter()
            self._idle_timed_out = False
            # If speech just started, prepend the pre-buffer to capture audio before VAD detection
            if speech_just_started:
                self.audio_buffer.extend(self._pre_buffer)
                self._speech_just_started = True
                # 创建流式ASR引擎，设置回调
                self._streaming_asr = self.asr.create_streaming_engine()
                self._streaming_asr.set_on_partial(self._emit_partial)
                # 将 pre-buffer 转换为 float32 并输入流式引擎
                if self._pre_buffer:
                    pre_audio = np.frombuffer(bytes(self._pre_buffer), dtype=np.int16)
                    pre_float32 = pre_audio.astype(np.float32) / 32768.0
                    self._streaming_asr.feed_chunk(pre_float32)
            self.audio_buffer.extend(audio_bytes)
            buffer_duration = len(self.audio_buffer) / 32000
            self._emit_status("speaking", buffer_duration=buffer_duration)

            # 将当前音频块输入流式引擎
            if self._streaming_asr:
                audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
                audio_float32 = audio_int16.astype(np.float32) / 32768.0
                self._streaming_asr.feed_chunk(audio_float32)
        else:
            # Maintain rolling pre-buffer when not in speech
            if not self._speech_just_started:
                self._pre_buffer.extend(audio_bytes)
                # Keep only the last 100ms
                if len(self._pre_buffer) > self._pre_buffer_size:
                    self._pre_buffer = self._pre_buffer[-self._pre_buffer_size:]

        # Idle timeout detection (only when not actively speaking)
        if not vad_result["is_speech"] and not self._speech_just_started and not self._idle_timed_out:
            idle_seconds = time.perf_counter() - self._last_speech_time

            if idle_seconds >= self.IDLE_TIMEOUT_SECONDS:
                self._idle_timed_out = True
                logger.info(f"[IDLE] Timeout after {idle_seconds:.1f}s of silence")
                self._emit_status("idle_timeout")
                return {"type": "idle_timeout"}

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

            self.audio_buffer.clear()
            self._pre_buffer.clear()
            self._speech_just_started = False
            self.vad.reset()

            # Step 1: ASR Transcription (使用流式引擎)
            self._emit_status("transcribing", audio_duration=audio_duration)
            t_asr_start = time.perf_counter()

            transcription = None
            if self._streaming_asr:
                transcription = self._streaming_asr.finalize()
                self._streaming_asr = None
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

                # Step 4: Output based on auto_input_mode (always via Tauri)
                if self._auto_input_mode == 'input':
                    self._emit_status("inputting", text=current_text)
                    if self._on_status:
                        self._on_status({
                            "type": "text_input_request",
                            "text": current_text,
                            "typewriter": True
                        })
                elif self._auto_input_mode == 'clipboard':
                    self._emit_status("copying", text=current_text)
                    if self._on_status:
                        self._on_status({
                            "type": "clipboard_request",
                            "text": current_text
                        })
                # 'none' mode: no automatic action

                # Step 5: Save to history for future context
                self.history_store.add(
                    text=current_text,
                    original=original_text,
                    duration=audio_duration,
                    language=correction_lang if self._correction_enabled else (self._asr_language or 'zh')
                )

            t_end = time.perf_counter()
            logger.info(f"[TIMING] Total processing time: {(t_end - t_start)*1000:.0f}ms")
            # Reset idle timer after processing completes
            self._last_speech_time = time.perf_counter()
            self._emit_status("recording")

        return result

    def reset(self) -> None:
        """Reset pipeline state."""
        self.audio_buffer.clear()
        self._pre_buffer.clear()
        self._speech_just_started = False
        self.vad.reset()
        if self._streaming_asr:
            self._streaming_asr.reset()
            self._streaming_asr = None
        # Reset idle tracking
        self._last_speech_time = 0.0
        self._idle_timed_out = False

    def update_llm_config(self, config: dict) -> None:
        """Update LLM configuration dynamically."""
        if self.llm:
            self.llm.reconfigure(**config)
        if self.translator:
            self.translator.reconfigure(**config)
        logger.info(f"LLM config updated: {config}")
