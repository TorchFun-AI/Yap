"""
Waveform Analyzer Module
Analyzes audio data and generates frequency band levels for visualization.
"""

import numpy as np
from typing import List


class WaveformAnalyzer:
    """Analyzes audio data to generate waveform visualization levels."""

    # Frequency band boundaries (Hz)
    # 5 bands: low, mid-low, mid, mid-high, high
    BAND_EDGES = [20, 150, 400, 1000, 3000, 8000]

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self._buffer = np.array([], dtype=np.int16)
        # Minimum samples needed for FFT (about 32ms at 16kHz)
        self._min_samples = 512

    def analyze(self, audio_bytes: bytes) -> List[float]:
        """
        Analyze audio chunk and return 5 normalized frequency band levels.

        Args:
            audio_bytes: Raw audio bytes (int16)

        Returns:
            List of 5 float values (0.0 - 1.0) representing frequency band levels
        """
        # Convert bytes to numpy array
        audio_data = np.frombuffer(audio_bytes, dtype=np.int16)

        # Append to buffer
        self._buffer = np.concatenate([self._buffer, audio_data])

        # Keep only recent samples (about 64ms worth)
        max_samples = self._min_samples * 2
        if len(self._buffer) > max_samples:
            self._buffer = self._buffer[-max_samples:]

        # Need minimum samples for meaningful FFT
        if len(self._buffer) < self._min_samples:
            return [0.0, 0.0, 0.0, 0.0, 0.0]

        # Apply window function to reduce spectral leakage
        windowed = self._buffer[-self._min_samples:] * np.hanning(self._min_samples)

        # Perform FFT
        fft_result = np.fft.rfft(windowed)
        fft_magnitude = np.abs(fft_result)

        # Calculate frequency resolution
        freq_resolution = self.sample_rate / self._min_samples
        freqs = np.fft.rfftfreq(self._min_samples, 1.0 / self.sample_rate)

        # Calculate energy in each frequency band
        levels = []
        for i in range(len(self.BAND_EDGES) - 1):
            low_freq = self.BAND_EDGES[i]
            high_freq = self.BAND_EDGES[i + 1]

            # Find indices for this frequency band
            low_idx = int(low_freq / freq_resolution)
            high_idx = int(high_freq / freq_resolution)

            # Clamp indices
            low_idx = max(0, min(low_idx, len(fft_magnitude) - 1))
            high_idx = max(low_idx + 1, min(high_idx, len(fft_magnitude)))

            # Calculate band energy (RMS of magnitudes)
            if high_idx > low_idx:
                band_energy = np.sqrt(np.mean(fft_magnitude[low_idx:high_idx] ** 2))
            else:
                band_energy = 0.0

            levels.append(band_energy)

        # Normalize levels to 0-1 range
        # Use dynamic normalization based on max energy
        max_level = max(levels) if levels else 1.0
        if max_level > 0:
            # Apply logarithmic scaling for better visual response
            normalized = []
            for level in levels:
                # Normalize and apply log scaling
                norm = level / max_level
                # Apply power curve for better visual response
                norm = np.power(norm, 0.6)
                normalized.append(float(min(1.0, max(0.0, norm))))
            return normalized
        else:
            return [0.0, 0.0, 0.0, 0.0, 0.0]

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
