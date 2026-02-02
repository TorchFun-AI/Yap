"""
Recording Session Manager
Manages audio capture sessions and coordinates with the processing pipeline.
"""

import asyncio
import threading
from typing import Callable, Optional
from .audio_capture import AudioCapture
from .pipeline import AudioPipeline
from .waveform_analyzer import get_analyzer, broadcast_waveform


class RecordingSession:
    """Manages a single recording session."""

    def __init__(self, on_result: Callable[[dict], None]):
        self._on_result = on_result
        self._audio_capture = AudioCapture()
        self._pipeline = AudioPipeline(on_status=self._send_result)
        self._is_running = False
        self._process_thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def start(self, config: Optional[dict] = None) -> None:
        """Start the recording session."""
        if self._is_running:
            return

        self._is_running = True
        self._loop = asyncio.get_event_loop()

        # Notify starting status before model loading
        self._on_result({"type": "status", "status": "starting"})

        # Apply LLM config BEFORE initialize (so LLM client uses correct config)
        if config:
            llm_config = {}
            if config.get("llmApiKey"):
                llm_config["api_key"] = config["llmApiKey"]
            if config.get("llmApiBase"):
                llm_config["api_base"] = config["llmApiBase"]
            if config.get("llmModel"):
                llm_config["model"] = config["llmModel"]
            if config.get("llmTimeout"):
                llm_config["timeout"] = config["llmTimeout"]
            if config.get("llmTemperature") is not None:
                llm_config["temperature"] = config["llmTemperature"]
            if llm_config:
                self._pipeline.update_llm_config(llm_config)

        # Initialize pipeline (loads ASR model and LLM client)
        self._pipeline.initialize()

        # Apply runtime config
        if config:
            asr_language = config.get("language", "auto")
            correction_enabled = config.get("correctionEnabled", True)
            target_language = config.get("targetLanguage", None)
            asr_model_path = config.get("asrModelPath", None)
            self._pipeline.set_config(
                correction_enabled=correction_enabled,
                target_language=target_language,
                asr_language=asr_language,
                asr_model_path=asr_model_path
            )

        self._audio_capture.start(callback=self._on_audio_chunk)
        self._on_result({"type": "status", "status": "recording"})

    def _on_audio_chunk(self, audio_bytes: bytes) -> None:
        """Process audio chunk from capture."""
        if not self._is_running:
            return
        # Analyze waveform and broadcast to connected clients
        analyzer = get_analyzer()
        levels = analyzer.analyze(audio_bytes)
        broadcast_waveform(levels)
        # Process through ASR pipeline
        result = self._pipeline.process_chunk(audio_bytes)
        self._send_result(result)

    def _send_result(self, result: dict) -> None:
        """Send result back via callback (thread-safe)."""
        if self._loop and self._on_result:
            self._loop.call_soon_threadsafe(self._on_result, result)

    def stop(self) -> None:
        """Stop the recording session."""
        self._is_running = False
        self._audio_capture.stop()
        self._pipeline.reset()
        self._on_result({"type": "status", "status": "stopped"})

    def update_config(self, config: dict) -> None:
        """Update runtime configuration during recording."""
        if not self._is_running:
            return
        asr_language = config.get("language")
        correction_enabled = config.get("correctionEnabled")
        target_language = config.get("targetLanguage")
        asr_model_path = config.get("asrModelPath")
        self._pipeline.set_config(
            correction_enabled=correction_enabled,
            target_language=target_language,
            asr_language=asr_language,
            asr_model_path=asr_model_path
        )

    def update_llm_config(self, config: dict) -> None:
        """Update LLM configuration dynamically."""
        self._pipeline.update_llm_config(config)

    @property
    def is_running(self) -> bool:
        return self._is_running
