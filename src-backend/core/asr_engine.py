"""
ASR (Automatic Speech Recognition) Engine
Uses MLX Audio FunASR for speech-to-text transcription on Apple Silicon.
"""

import os
import logging
from typing import Optional, Generator, Callable
from concurrent.futures import ThreadPoolExecutor
import asyncio

import numpy as np

logger = logging.getLogger(__name__)


def _detect_model_type(model_path: str) -> str:
    """根据模型路径检测模型类型"""
    if not model_path:
        return "funasr"
    path_lower = model_path.lower()
    if "whisper" in path_lower:
        return "whisper"
    return "funasr"


class ASREngine:
    """Automatic Speech Recognition engine using MLX Audio FunASR."""

    def __init__(self, model_path: str = None):
        default_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "Fun-ASR-MLT-Nano-2512-4bit")
        self.model_path = os.getenv("ASR_MODEL_PATH", model_path or default_path)
        self.default_language = os.getenv("ASR_DEFAULT_LANGUAGE", "zh")
        self.model = None
        self.model_type = None
        self.is_initialized = False
        self.executor = ThreadPoolExecutor(max_workers=2)

    def initialize(self) -> None:
        """Initialize the ASR model based on model type."""
        if self.is_initialized:
            return

        try:
            self.model_type = _detect_model_type(self.model_path)
            logger.info(f"Loading {self.model_type} model: {self.model_path}")

            if self.model_type == "whisper":
                from mlx_audio.stt.models.whisper import Model
                self.model = Model.from_pretrained(self.model_path)
            else:
                from mlx_audio.stt.models.funasr import Model
                self.model = Model.from_pretrained(self.model_path, fix_mistral_regex=True)

            self.is_initialized = True
            logger.info(f"{self.model_type} model loaded successfully")
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

    def transcribe_stream(
        self,
        audio_float32: np.ndarray,
        language: Optional[str] = None,
        on_partial: Optional[Callable[[str], None]] = None
    ) -> Optional[str]:
        """
        流式转录音频数据。

        Args:
            audio_float32: 音频数据
            language: 语言代码
            on_partial: 部分结果回调函数，每次有新文本时调用

        Returns:
            最终完整转录文本
        """
        if not self.is_initialized:
            self.initialize()

        # Whisper 模型不支持流式，回退到普通转录
        if self.model_type == "whisper":
            result = self.transcribe(audio_float32, language)
            if result and on_partial:
                on_partial(result)
            return result

        try:
            lang = language or self.default_language
            accumulated_text = ""

            for chunk in self.model.generate(audio_float32, stream=True, language=lang):
                # chunk 可能是字符串或对象
                chunk_text = chunk if isinstance(chunk, str) else str(chunk)
                accumulated_text += chunk_text

                if on_partial and accumulated_text.strip():
                    on_partial(accumulated_text.strip())

            return accumulated_text.strip() if accumulated_text else None
        except Exception as e:
            logger.error(f"Streaming transcription failed: {e}")
            return None

    async def transcribe_async(self, audio_float32: np.ndarray, language: Optional[str] = None) -> Optional[str]:
        """Async wrapper for transcribe."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self.transcribe, audio_float32, language)

    def set_model_path(self, model_path: str) -> None:
        """设置模型路径（需要重新初始化）"""
        if model_path != self.model_path:
            self.model_path = model_path
            self.model_type = None
            self.is_initialized = False
            self.model = None
            logger.info(f"ASR model path changed to: {model_path}")
