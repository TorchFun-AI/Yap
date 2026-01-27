"""
Audio Capture Module
Captures audio from microphone using sounddevice.
"""

import threading
import queue
from typing import Callable, Optional
import numpy as np
import sounddevice as sd


class AudioCapture:
    """Captures audio from microphone using sounddevice."""

    SAMPLE_RATE = 16000
    CHANNELS = 1
    BLOCK_SIZE = 4096
    DTYPE = np.int16

    def __init__(self):
        self._stream: Optional[sd.InputStream] = None
        self._audio_queue: queue.Queue[bytes] = queue.Queue()
        self._is_running = False
        self._callback: Optional[Callable[[bytes], None]] = None

    def _audio_callback(self, indata: np.ndarray, frames: int,
                        time_info: dict, status: sd.CallbackFlags) -> None:
        """Callback for sounddevice stream."""
        if status:
            print(f"Audio callback status: {status}")
        if self._is_running:
            audio_bytes = indata.tobytes()
            self._audio_queue.put(audio_bytes)
            if self._callback:
                self._callback(audio_bytes)

    def start(self, callback: Optional[Callable[[bytes], None]] = None) -> None:
        """Start audio capture."""
        if self._is_running:
            return

        self._callback = callback
        self._is_running = True
        self._stream = sd.InputStream(
            samplerate=self.SAMPLE_RATE,
            channels=self.CHANNELS,
            dtype=self.DTYPE,
            blocksize=self.BLOCK_SIZE,
            callback=self._audio_callback,
        )
        self._stream.start()

    def stop(self) -> None:
        """Stop audio capture."""
        self._is_running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._callback = None
        # Clear the queue
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

    def get_chunk(self, timeout: float = 0.1) -> Optional[bytes]:
        """Get audio chunk from queue."""
        try:
            return self._audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    @property
    def is_running(self) -> bool:
        return self._is_running

    @staticmethod
    def list_devices() -> list[dict]:
        """List available audio input devices."""
        devices = sd.query_devices()
        input_devices = []
        for i, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                input_devices.append({
                    'id': i,
                    'name': dev['name'],
                    'channels': dev['max_input_channels'],
                    'default': i == sd.default.device[0],
                })
        return input_devices
