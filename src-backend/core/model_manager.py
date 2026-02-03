"""
ASR Model Manager
Manages ASR model downloads from Hugging Face mlx-community.
Only supports MLX format models for Apple Silicon optimization.
Uses HuggingFace default cache path (~/.cache/huggingface/hub/).
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Optional
import threading

logger = logging.getLogger(__name__)

# HuggingFace 默认缓存目录
HF_CACHE_DIR = Path.home() / ".cache" / "huggingface" / "hub"

# 预定义的 MLX 格式 ASR 模型列表 (来自 mlx-community)
MLX_ASR_MODELS = [
    {
        "id": "mlx-community/Fun-ASR-MLT-Nano-2512-4bit",
        "name": "FunASR Nano 4bit",
        "size": "~1.3GB",
        "description": "多语言语音识别模型 (4-bit 量化)",
    },
    {
        "id": "mlx-community/Fun-ASR-MLT-Nano-2512-8bit",
        "name": "FunASR Nano 8bit",
        "size": "~2.5GB",
        "description": "多语言语音识别模型 (8-bit 量化)",
    },
    {
        "id": "mlx-community/whisper-large-v3-mlx",
        "name": "Whisper Large V3",
        "size": "~3GB",
        "description": "OpenAI Whisper 大模型 MLX 版",
    },
]


class ModelManager:
    """ASR 模型管理器 (仅支持 MLX 格式，使用 HuggingFace 缓存)"""

    def __init__(self):
        self._download_progress = {}
        self._download_lock = threading.Lock()
        self._download_tasks = {}

    def list_local_models(self) -> List[Dict]:
        """列出本地已缓存的模型（扫描 HuggingFace 缓存目录）"""
        models = []
        if not HF_CACHE_DIR.exists():
            return models

        # 遍历预定义模型，检查是否已缓存
        for model_info in MLX_ASR_MODELS:
            model_id = model_info["id"]
            # HuggingFace 缓存目录格式: models--org--name
            cache_name = "models--" + model_id.replace("/", "--")
            cache_path = HF_CACHE_DIR / cache_name

            if cache_path.exists() and cache_path.is_dir():
                # 检查是否有 snapshots 目录（表示模型已下载）
                snapshots_dir = cache_path / "snapshots"
                if snapshots_dir.exists() and any(snapshots_dir.iterdir()):
                    models.append({
                        "id": model_id,
                        "name": model_info["name"],
                        "size": self._get_dir_size(cache_path),
                    })
        return models

    def list_available_models(self) -> List[Dict]:
        """列出可下载的 MLX 格式模型"""
        local_model_ids = {m["id"] for m in self.list_local_models()}
        result = []
        for model in MLX_ASR_MODELS:
            result.append({
                **model,
                "downloaded": model["id"] in local_model_ids,
            })
        return result

    def download_model(self, model_id: str, on_progress=None) -> Dict:
        """从 Hugging Face 下载 MLX 格式模型到默认缓存目录"""
        try:
            from huggingface_hub import snapshot_download

            # 设置 hf-mirror 镜像
            os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

            logger.info(f"Downloading model {model_id} to HuggingFace cache (via hf-mirror)")

            with self._download_lock:
                self._download_progress[model_id] = {"status": "downloading", "progress": 0}

            # 下载模型到默认缓存目录
            snapshot_download(
                repo_id=model_id,
                endpoint="https://hf-mirror.com",
            )

            with self._download_lock:
                self._download_progress[model_id] = {"status": "completed", "progress": 100}

            return {"success": True, "model_id": model_id}
        except Exception as e:
            logger.error(f"Model download failed: {e}")
            with self._download_lock:
                self._download_progress[model_id] = {"status": "failed", "error": str(e)}
            return {"success": False, "error": str(e)}

    def get_download_progress(self, model_id: str) -> Optional[Dict]:
        """获取下载进度"""
        with self._download_lock:
            return self._download_progress.get(model_id)

    def _get_dir_size(self, path: Path) -> str:
        """获取目录大小"""
        total = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
        if total > 1e9:
            return f"{total/1e9:.1f}GB"
        return f"{total/1e6:.0f}MB"
