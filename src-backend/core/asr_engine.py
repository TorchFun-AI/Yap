"""
ASR (Automatic Speech Recognition) Engine
Uses MLX Audio FunASR for speech-to-text transcription on Apple Silicon.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Callable
from concurrent.futures import ThreadPoolExecutor
import asyncio

import numpy as np

logger = logging.getLogger(__name__)

# 默认模型 ID
DEFAULT_MODEL_ID = "mlx-community/Fun-ASR-MLT-Nano-2512-4bit"

# HuggingFace 缓存目录
HF_CACHE_DIR = Path.home() / ".cache" / "huggingface" / "hub"


def _get_local_model_path(model_id: str) -> Optional[str]:
    """获取本地缓存的模型路径，如果不存在返回 None"""
    cache_name = "models--" + model_id.replace("/", "--")
    cache_path = HF_CACHE_DIR / cache_name / "snapshots"

    if not cache_path.exists():
        return None

    # 获取最新的 snapshot
    snapshots = list(cache_path.iterdir())
    if not snapshots:
        return None

    # 返回第一个 snapshot 的路径
    return str(snapshots[0])


def _detect_model_type(model_id: str) -> str:
    """根据模型 ID 检测模型类型"""
    if not model_id:
        return "funasr"
    id_lower = model_id.lower()
    if "whisper" in id_lower:
        return "whisper"
    return "funasr"


class ASREngine:
    """Automatic Speech Recognition engine using MLX Audio FunASR."""

    def __init__(self, model_id: str = None):
        self.model_id = os.getenv("ASR_MODEL_ID", model_id or DEFAULT_MODEL_ID)
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
            # 设置 hf-mirror 镜像加速下载（如果需要下载）
            os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

            self.model_type = _detect_model_type(self.model_id)

            # 优先使用本地缓存路径
            local_path = _get_local_model_path(self.model_id)
            model_path = local_path or self.model_id

            logger.info(f"Loading {self.model_type} model: {model_path}")

            if self.model_type == "whisper":
                from mlx_audio.stt.models.whisper import Model
                self.model = Model.from_pretrained(model_path)
            else:
                from mlx_audio.stt.models.funasr import Model
                self.model = Model.from_pretrained(model_path, fix_mistral_regex=True)

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

    def set_model_id(self, model_id: str) -> None:
        """设置模型 ID（需要重新初始化）"""
        logger.info(f"set_model_id called with: {model_id}, current: {self.model_id}")
        if model_id != self.model_id:
            self.model_id = model_id
            self.model_type = None
            self.is_initialized = False
            self.model = None
            logger.info(f"ASR model ID changed to: {model_id}")
