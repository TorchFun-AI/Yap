"""
ASR (Automatic Speech Recognition) Engine
Uses MLX Audio FunASR for speech-to-text transcription on Apple Silicon.
"""

import os
import logging
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
import asyncio

import numpy as np

logger = logging.getLogger(__name__)


class ASREngine:
    """Automatic Speech Recognition engine using MLX Audio FunASR."""

    def __init__(self, model_path: str = None):
        default_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "Fun-ASR-MLT-Nano-2512-4bit")
        self.model_path = os.getenv("ASR_MODEL_PATH", model_path or default_path)
        self.default_language = os.getenv("ASR_DEFAULT_LANGUAGE", "zh")
        self.model = None
        self.is_initialized = False
        self.executor = ThreadPoolExecutor(max_workers=2)

    def initialize(self) -> None:
        """Initialize the MLX Audio FunASR model."""
        if self.is_initialized:
            return

        try:
            from mlx_audio.stt.models.funasr import Model

            logger.info(f"Loading model: {self.model_path}")
            self.model = Model.from_pretrained(self.model_path, fix_mistral_regex=True)
            self.is_initialized = True
            logger.info("MLX Audio FunASR model loaded successfully")
        except Exception as e:
            logger.error(f"Model loading failed: {e}")
            raise

    def transcribe(self, audio_float32: np.ndarray, language: Optional[str] = None) -> Optional[str]:
        """Transcribe audio data to text."""
        if not self.is_initialized:
            self.initialize()

        try:
            lang = language or self.default_language
            result = self.model.generate(audio_float32, language=lang)
            text = result.text if hasattr(result, 'text') else str(result)
            return text.strip() if text else None
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return None

    async def transcribe_async(self, audio_float32: np.ndarray, language: Optional[str] = None) -> Optional[str]:
        """Async wrapper for transcribe."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self.transcribe, audio_float32, language)
