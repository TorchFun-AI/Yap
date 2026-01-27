"""
VAD (Voice Activity Detection) Engine
Uses Silero VAD for accurate real-time voice activity detection.
"""

import numpy as np
from silero_vad import load_silero_vad
import torch


class VADEngine:
    """Voice Activity Detection engine using Silero VAD."""

    def __init__(self, threshold: float = 0.5, sample_rate: int = 16000):
        self.threshold = threshold
        self.sample_rate = sample_rate
        self.chunk_size = 512  # Silero VAD requires 512 samples at 16kHz
        self.model = None
        self.is_initialized = False
        self._buffer = np.array([], dtype=np.float32)
        self._speech_started = False
        self._silence_frames = 0
        self._max_silence_frames = 15  # ~0.48s silence to end speech

    def initialize(self) -> None:
        """Initialize the Silero VAD model."""
        if self.is_initialized:
            return
        self.model = load_silero_vad()
        self.is_initialized = True

    def process_chunk(self, audio_bytes: bytes) -> dict:
        """Process audio chunk and detect voice activity."""
        if not self.is_initialized:
            self.initialize()

        audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0
        self._buffer = np.concatenate([self._buffer, audio_float32])

        is_speech = False
        confidence = 0.0

        while len(self._buffer) >= self.chunk_size:
            chunk = self._buffer[:self.chunk_size]
            self._buffer = self._buffer[self.chunk_size:]
            audio_tensor = torch.from_numpy(chunk)
            conf = self.model(audio_tensor, self.sample_rate).item()
            confidence = max(confidence, conf)
            if conf >= self.threshold:
                is_speech = True

        if is_speech:
            self._speech_started = True
            self._silence_frames = 0
        elif self._speech_started:
            self._silence_frames += 1

        speech_ended = self._speech_started and self._silence_frames >= self._max_silence_frames

        return {
            "is_speech": is_speech,
            "confidence": confidence,
            "speech_started": self._speech_started,
            "speech_ended": speech_ended,
        }

    def reset(self) -> None:
        """Reset VAD state."""
        self._buffer = np.array([], dtype=np.float32)
        self._speech_started = False
        self._silence_frames = 0
        if self.model is not None:
            self.model.reset_states()
