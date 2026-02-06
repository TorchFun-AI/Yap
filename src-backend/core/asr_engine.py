"""
ASR (Automatic Speech Recognition) Engine
Uses MLX Audio FunASR for speech-to-text transcription on Apple Silicon.
"""

import os
import logging
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Callable
from concurrent.futures import ThreadPoolExecutor, Future
import asyncio

import numpy as np

# MLX Audio 模型 - 静态导入以支持 PyInstaller 打包
from mlx_audio.stt.models.whisper import Model as WhisperModel
from mlx_audio.stt.models.funasr import Model as FunASRModel

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

    # 获取最新的 snapshot（过滤掉隐藏文件和非目录项）
    snapshots = [p for p in cache_path.iterdir() if p.is_dir() and not p.name.startswith('.')]
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


class StreamingASREngine(ABC):
    """流式ASR引擎抽象基类，支持边录边识别"""

    @abstractmethod
    def feed_chunk(self, audio_chunk: np.ndarray) -> None:
        """输入音频块"""
        pass

    @abstractmethod
    def get_partial(self) -> Optional[str]:
        """获取部分结果，如果没有新结果返回 None"""
        pass

    @abstractmethod
    def finalize(self) -> str:
        """结束输入，获取最终结果"""
        pass

    @abstractmethod
    def reset(self) -> None:
        """重置状态，准备下一次识别"""
        pass

    @abstractmethod
    def set_on_partial(self, callback: Optional[Callable[[str], None]]) -> None:
        """设置部分结果回调函数"""
        pass


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
                self.model = WhisperModel.from_pretrained(model_path)
            else:
                self.model = FunASRModel.from_pretrained(model_path, fix_mistral_regex=True)

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

    def create_streaming_engine(self) -> "StreamingASREngine":
        """创建流式ASR引擎实例"""
        if not self.is_initialized:
            self.initialize()

        if self.model_type == "whisper":
            return WhisperStreamingASR(self.model, self.default_language)
        else:
            return FunASRStreamingASR(self.model, self.default_language)


class WhisperStreamingASR(StreamingASREngine):
    """Whisper 流式ASR实现，使用后台线程持续识别"""

    def __init__(self, model, language: str = "zh"):
        self.model = model
        self.language = language
        self._audio_buffer = []
        self._lock = threading.Lock()
        self._model_lock = threading.Lock()  # 保护 GPU 模型访问
        self._partial_result: Optional[str] = None
        self._finalized = False
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._new_audio_event = threading.Event()
        self._on_partial: Optional[Callable[[str], None]] = None

    def set_on_partial(self, callback: Optional[Callable[[str], None]]) -> None:
        """设置部分结果回调函数"""
        self._on_partial = callback

    def _worker_loop(self):
        """后台工作线程，持续进行识别"""
        logger.info("[STREAMING] Worker thread started")
        while not self._stop_event.is_set():
            # 短暂等待新音频
            self._new_audio_event.wait(timeout=0.1)
            self._new_audio_event.clear()

            if self._stop_event.is_set():
                break

            with self._lock:
                if not self._audio_buffer:
                    continue
                buffer_copy = list(self._audio_buffer)

            try:
                combined = np.concatenate(buffer_copy)
                with self._model_lock:
                    if self._stop_event.is_set():
                        break
                    result = self.model.generate(combined, language=self.language)
                text = result.text if hasattr(result, 'text') else str(result)
                if text and text.strip():
                    new_result = text.strip()
                    if new_result != self._partial_result:
                        self._partial_result = new_result
                        # 事件驱动：结果更新时立即回调
                        if self._on_partial:
                            self._on_partial(new_result)
            except Exception as e:
                logger.warning(f"Whisper recognize failed: {e}")

        logger.info("[STREAMING] Worker thread stopped")

    def feed_chunk(self, audio_chunk: np.ndarray) -> None:
        """输入音频块（非阻塞）"""
        if self._finalized:
            return
        with self._lock:
            self._audio_buffer.append(audio_chunk)

        # 启动工作线程（如果还没启动）
        if self._worker_thread is None:
            logger.info("[STREAMING] Starting worker thread...")
            self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._worker_thread.start()

        # 通知工作线程有新音频
        self._new_audio_event.set()

    def get_partial(self) -> Optional[str]:
        """获取部分结果（非阻塞）"""
        return self._partial_result

    def finalize(self) -> str:
        """结束输入，获取最终结果"""
        if self._finalized:
            return self._partial_result or ""

        self._finalized = True
        self._stop_event.set()
        self._new_audio_event.set()  # 唤醒工作线程

        if self._worker_thread:
            self._worker_thread.join(timeout=2)

        # 最终识别
        with self._lock:
            if not self._audio_buffer:
                return self._partial_result or ""
            combined = np.concatenate(self._audio_buffer)

        try:
            with self._model_lock:
                result = self.model.generate(combined, language=self.language)
            text = result.text if hasattr(result, 'text') else str(result)
            return text.strip() if text else (self._partial_result or "")
        except Exception as e:
            logger.error(f"Whisper finalize failed: {e}")
            return self._partial_result or ""

    def reset(self) -> None:
        """重置状态"""
        self._finalized = True
        self._stop_event.set()
        self._new_audio_event.set()
        if self._worker_thread:
            self._worker_thread.join(timeout=1)
        with self._lock:
            self._audio_buffer = []
        self._partial_result = None
        self._worker_thread = None
        self._stop_event.clear()
        self._new_audio_event.clear()
        self._finalized = False


class FunASRStreamingASR(StreamingASREngine):
    """FunASR 流式实现，使用后台线程持续识别"""

    def __init__(self, model, language: str = "zh"):
        self.model = model
        self.language = language
        self._audio_buffer = []
        self._lock = threading.Lock()
        self._model_lock = threading.Lock()  # 保护 GPU 模型访问
        self._partial_result: Optional[str] = None
        self._finalized = False
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._new_audio_event = threading.Event()
        self._on_partial: Optional[Callable[[str], None]] = None

    def set_on_partial(self, callback: Optional[Callable[[str], None]]) -> None:
        """设置部分结果回调函数"""
        self._on_partial = callback

    def _worker_loop(self):
        """后台工作线程，持续进行识别"""
        while not self._stop_event.is_set():
            self._new_audio_event.wait(timeout=0.1)
            self._new_audio_event.clear()

            if self._stop_event.is_set():
                break

            with self._lock:
                if not self._audio_buffer:
                    continue
                buffer_copy = list(self._audio_buffer)

            try:
                combined = np.concatenate(buffer_copy)
                with self._model_lock:
                    if self._stop_event.is_set():
                        break
                    result = self.model.generate(combined, language=self.language)
                text = result.text if hasattr(result, 'text') else str(result)
                if text and text.strip():
                    new_result = text.strip()
                    if new_result != self._partial_result:
                        self._partial_result = new_result
                        if self._on_partial:
                            self._on_partial(new_result)
            except Exception as e:
                logger.warning(f"FunASR recognize failed: {e}")

    def feed_chunk(self, audio_chunk: np.ndarray) -> None:
        """输入音频块（非阻塞）"""
        if self._finalized:
            return
        with self._lock:
            self._audio_buffer.append(audio_chunk)

        if self._worker_thread is None:
            self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._worker_thread.start()

        self._new_audio_event.set()

    def get_partial(self) -> Optional[str]:
        """获取部分结果（非阻塞）"""
        return self._partial_result

    def finalize(self) -> str:
        """结束输入，获取最终结果"""
        if self._finalized:
            return self._partial_result or ""

        self._finalized = True
        self._stop_event.set()
        self._new_audio_event.set()

        if self._worker_thread:
            self._worker_thread.join(timeout=2)

        with self._lock:
            if not self._audio_buffer:
                return self._partial_result or ""
            combined = np.concatenate(self._audio_buffer)

        try:
            with self._model_lock:
                result = self.model.generate(combined, language=self.language)
            text = result.text if hasattr(result, 'text') else str(result)
            return text.strip() if text else (self._partial_result or "")
        except Exception as e:
            logger.error(f"FunASR finalize failed: {e}")
            return self._partial_result or ""

    def reset(self) -> None:
        """重置状态"""
        self._finalized = True
        self._stop_event.set()
        self._new_audio_event.set()
        if self._worker_thread:
            self._worker_thread.join(timeout=1)
        with self._lock:
            self._audio_buffer = []
        self._partial_result = None
        self._worker_thread = None
        self._stop_event.clear()
        self._new_audio_event.clear()
        self._finalized = False
