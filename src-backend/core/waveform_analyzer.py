"""
Waveform Analyzer Module
Analyzes audio data and generates frequency band levels for visualization.
"""

import numpy as np
from typing import List


class WaveformAnalyzer:
    """Analyzes audio data to generate waveform visualization levels."""

    # Sample 4 bins from the speech-dominant range, then mirror for symmetric 7-bar display
    # Bins cover ~150-1100 Hz at 16kHz — where most speech energy lives
    SAMPLE_INDICES = [5, 12, 22, 35]

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self._buffer = np.array([], dtype=np.int16)
        # FFT size 512
        self._min_samples = 512

    def analyze(self, audio_bytes: bytes) -> List[float]:
        """
        Analyze audio chunk and return 7 normalized levels (symmetric: center tallest).

        Args:
            audio_bytes: Raw audio bytes (int16)

        Returns:
            List of 7 float values (0.0 - 1.0), symmetric pattern
        """
        # Convert bytes to numpy array
        audio_data = np.frombuffer(audio_bytes, dtype=np.int16)

        # Append to buffer
        self._buffer = np.concatenate([self._buffer, audio_data])

        # Keep only recent samples
        max_samples = self._min_samples * 2
        if len(self._buffer) > max_samples:
            self._buffer = self._buffer[-max_samples:]

        # Need minimum samples for FFT
        if len(self._buffer) < self._min_samples:
            return [0.0] * 7

        # Apply window function
        windowed = self._buffer[-self._min_samples:] * np.hanning(self._min_samples)

        # Perform FFT
        fft_result = np.fft.rfft(windowed)
        fft_magnitude = np.abs(fft_result)

        # Sample 4 points from speech range (low freq = most energy)
        raw = [float(fft_magnitude[i]) for i in self.SAMPLE_INDICES if i < len(fft_magnitude)]
        while len(raw) < 4:
            raw.append(0.0)

        # Normalize
        max_val = 4096.0 * 10
        normed = [min(1.0, v / max_val) for v in raw]

        # Mirror into symmetric 7-bar pattern: [edge, outer, inner, CENTER, inner, outer, edge]
        # raw[0]=bin5 is strongest (center), raw[3]=bin35 is weakest (edge)
        return [normed[3], normed[2], normed[1], normed[0], normed[1], normed[2], normed[3]]

    def reset(self):
        """Reset the analyzer buffer."""
        self._buffer = np.array([], dtype=np.int16)


# Global instance for shared access
_analyzer_instance: WaveformAnalyzer | None = None
_waveform_callbacks: List = []


def get_analyzer() -> WaveformAnalyzer:
    """Get or create the global waveform analyzer instance."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = WaveformAnalyzer()
    return _analyzer_instance


def register_waveform_callback(callback):
    """Register a callback to receive waveform data."""
    global _waveform_callbacks
    if callback not in _waveform_callbacks:
        _waveform_callbacks.append(callback)


def unregister_waveform_callback(callback):
    """Unregister a waveform callback."""
    global _waveform_callbacks
    if callback in _waveform_callbacks:
        _waveform_callbacks.remove(callback)


def broadcast_waveform(levels: List[float]):
    """Broadcast waveform levels to all registered callbacks."""
    global _waveform_callbacks
    for callback in _waveform_callbacks:
        try:
            callback(levels)
        except Exception:
            pass
