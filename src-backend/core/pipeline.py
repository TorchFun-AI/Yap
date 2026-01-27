"""
Audio Processing Pipeline
Coordinates VAD and ASR engines for real-time voice processing.
"""

import numpy as np
from .vad_engine import VADEngine
from .asr_engine import ASREngine


class AudioPipeline:
    """Main audio processing pipeline."""

    def __init__(self, on_status=None):
        self.vad = VADEngine()
        self.asr = ASREngine()
        self.audio_buffer = bytearray()
        self.is_initialized = False
        self._on_status = on_status

    def _emit_status(self, status: str, **kwargs):
        """Emit status update."""
        if self._on_status:
            self._on_status({"type": "status", "status": status, **kwargs})

    def initialize(self) -> None:
        """Initialize all pipeline components."""
        self.vad.initialize()
        self.is_initialized = True

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
            self._emit_status("transcribing", audio_duration=len(self.audio_buffer) / 32000)
            audio_int16 = np.frombuffer(bytes(self.audio_buffer), dtype=np.int16)
            audio_float32 = audio_int16.astype(np.float32) / 32768.0

            transcription = self.asr.transcribe(audio_float32)
            self.audio_buffer.clear()
            self.vad.reset()

            if transcription:
                result = {
                    "type": "transcription",
                    "text": transcription,
                    "is_final": True,
                }
            self._emit_status("recording")

        return result

    def reset(self) -> None:
        """Reset pipeline state."""
        self.audio_buffer.clear()
        self.vad.reset()
