"""
ASR Model Manager
Manages ASR model downloads from Hugging Face mlx-community.
Only supports MLX format models for Apple Silicon optimization.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Optional
import threading

logger = logging.getLogger(__name__)

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
    """ASR 模型管理器 (仅支持 MLX 格式)"""

    def __init__(self, models_dir: str = None):
        default_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
        self.models_dir = models_dir or os.getenv("ASR_MODELS_DIR", default_dir)
        self._download_progress = {}
        self._download_lock = threading.Lock()
        self._download_tasks = {}

    def list_local_models(self) -> List[Dict]:
        """列出本地已下载的模型"""
        models = []
        models_path = Path(self.models_dir)
        if not models_path.exists():
            return models

        for item in models_path.iterdir():
            if item.is_dir() and (item / "config.json").exists():
                models.append({
                    "name": item.name,
                    "path": str(item),
                    "size": self._get_dir_size(item),
                })
        return models

    def list_available_models(self) -> List[Dict]:
        """列出可下载的 MLX 格式模型"""
        local_models = {m["name"] for m in self.list_local_models()}
        result = []
        for model in MLX_ASR_MODELS:
            model_name = model["id"].split("/")[-1]
            result.append({
                **model,
                "downloaded": model_name in local_models,
            })
        return result

    def download_model(self, model_id: str, on_progress=None) -> Dict:
        """从 Hugging Face 下载 MLX 格式模型 (使用 hf-mirror 镜像加速)"""
        try:
            from huggingface_hub import snapshot_download

            # 设置 hf-mirror 镜像
            os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

            # 模型保存目录：models/模型名
            model_name = model_id.split("/")[-1]
            local_dir = os.path.join(self.models_dir, model_name)

            logger.info(f"Downloading model {model_id} to {local_dir} (via hf-mirror)")

            with self._download_lock:
                self._download_progress[model_id] = {"status": "downloading", "progress": 0}

            # 下载模型
            path = snapshot_download(
                repo_id=model_id,
                local_dir=local_dir,
                local_dir_use_symlinks=False,
                endpoint="https://hf-mirror.com",
            )

            with self._download_lock:
                self._download_progress[model_id] = {"status": "completed", "progress": 100}

            return {"success": True, "path": path}
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
