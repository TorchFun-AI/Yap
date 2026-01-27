"""
Recording Session Manager
Manages audio capture sessions and coordinates with the processing pipeline.
"""

import asyncio
import threading
from typing import Callable, Optional
from .audio_capture import AudioCapture
from .pipeline import AudioPipeline


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

        # Initialize pipeline (loads ASR model) on start
        self._pipeline.initialize()

        self._audio_capture.start(callback=self._on_audio_chunk)
        self._on_result({"type": "status", "status": "recording"})

    def _on_audio_chunk(self, audio_bytes: bytes) -> None:
        """Process audio chunk from capture."""
        if not self._is_running:
            return
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

    @property
    def is_running(self) -> bool:
        return self._is_running
