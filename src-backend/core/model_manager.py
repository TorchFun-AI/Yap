"""
ASR Model Manager
Manages ASR model downloads from Hugging Face mlx-community.
Only supports MLX format models for Apple Silicon optimization.
Uses HuggingFace default cache path (~/.cache/huggingface/hub/).
"""

import os
import logging
import time
from pathlib import Path
from typing import List, Dict, Optional
import threading

from huggingface_hub import snapshot_download, HfApi

logger = logging.getLogger(__name__)


def format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes >= 1e9:
        return f"{size_bytes / 1e9:.2f} GB"
    elif size_bytes >= 1e6:
        return f"{size_bytes / 1e6:.2f} MB"
    elif size_bytes >= 1e3:
        return f"{size_bytes / 1e3:.2f} KB"
    return f"{size_bytes} B"


def format_speed(speed_bytes: float) -> str:
    """格式化下载速度"""
    if speed_bytes >= 1e6:
        return f"{speed_bytes / 1e6:.2f} MB/s"
    elif speed_bytes >= 1e3:
        return f"{speed_bytes / 1e3:.2f} KB/s"
    return f"{speed_bytes:.0f} B/s"


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

    def _get_model_info(self, model_id: str) -> Optional[Dict]:
        """获取模型信息"""
        for model in MLX_ASR_MODELS:
            if model["id"] == model_id:
                return model
        return None

    def _get_cache_path(self, model_id: str) -> Path:
        """获取模型缓存路径"""
        cache_name = "models--" + model_id.replace("/", "--")
        return HF_CACHE_DIR / cache_name

    def _get_dir_size_bytes(self, path: Path) -> int:
        """获取目录大小（字节）"""
        if not path.exists():
            return 0
        return sum(f.stat().st_size for f in path.rglob('*') if f.is_file())

    def _get_repo_size(self, model_id: str, use_mirror: bool = True) -> int:
        """从 HuggingFace API 获取模型仓库总大小"""
        try:
            endpoint = "https://hf-mirror.com" if use_mirror else None
            api = HfApi(endpoint=endpoint)
            # 使用 list_repo_tree 获取文件列表和大小
            files = list(api.list_repo_tree(model_id, repo_type="model"))
            total_size = sum(f.size for f in files if hasattr(f, 'size') and f.size)
            return total_size
        except Exception as e:
            logger.warning(f"Failed to get repo size for {model_id}: {e}")
            return 0

    def download_model(self, model_id: str, use_mirror: bool = True) -> Dict:
        """从 Hugging Face 下载 MLX 格式模型到默认缓存目录

        Args:
            model_id: 模型 ID
            use_mirror: 是否使用 hf-mirror 镜像（国内用户建议开启）
        """
        try:
            endpoint = "https://hf-mirror.com" if use_mirror else None

            if use_mirror:
                os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
                logger.info(f"Downloading model {model_id} (via hf-mirror)")
            else:
                os.environ.pop("HF_ENDPOINT", None)
                logger.info(f"Downloading model {model_id} (direct)")

            # 获取模型实际大小
            cache_path = self._get_cache_path(model_id)
            estimated_size = self._get_repo_size(model_id, use_mirror)

            with self._download_lock:
                self._download_progress[model_id] = {
                    "status": "downloading",
                    "progress": 0,
                    "downloaded": "0 B",
                    "total": format_size(estimated_size) if estimated_size else "unknown",
                    "speed": "0 B/s",
                }

            # 启动进度监控线程
            stop_monitor = threading.Event()

            def monitor_progress():
                start_time = time.time()
                start_size = self._get_dir_size_bytes(cache_path)
                # 用于计算平滑速度的历史记录
                history = []
                history_window = 5  # 5秒滑动窗口

                while not stop_monitor.is_set():
                    current_size = self._get_dir_size_bytes(cache_path)
                    current_time = time.time()

                    # 记录历史数据点
                    history.append((current_time, current_size))
                    # 只保留最近 N 秒的数据
                    cutoff_time = current_time - history_window
                    history = [(t, s) for t, s in history if t >= cutoff_time]

                    # 计算滑动窗口内的平均速度
                    if len(history) >= 2:
                        time_diff = history[-1][0] - history[0][0]
                        size_diff = history[-1][1] - history[0][1]
                        speed = size_diff / time_diff if time_diff > 0 else 0
                    else:
                        # 使用总体平均速度作为后备
                        elapsed = current_time - start_time
                        speed = (current_size - start_size) / elapsed if elapsed > 0 else 0

                    # 计算进度
                    progress = (current_size / estimated_size * 100) if estimated_size > 0 else 0
                    progress = min(progress, 99)  # 下载完成前最多显示 99%

                    with self._download_lock:
                        self._download_progress[model_id] = {
                            "status": "downloading",
                            "progress": round(progress, 1),
                            "downloaded": format_size(current_size),
                            "total": format_size(estimated_size) if estimated_size else "unknown",
                            "speed": format_speed(speed),
                        }

                    stop_monitor.wait(1)  # 每秒更新一次

            monitor_thread = threading.Thread(target=monitor_progress, daemon=True)
            monitor_thread.start()

            try:
                # 下载模型到默认缓存目录
                snapshot_download(
                    repo_id=model_id,
                    endpoint=endpoint,
                )
            finally:
                stop_monitor.set()
                monitor_thread.join(timeout=2)

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

    def delete_model(self, model_id: str) -> Dict:
        """删除本地模型缓存

        Args:
            model_id: 模型 ID

        Returns:
            {"success": bool, "error": str (optional)}
        """
        import shutil

        try:
            cache_path = self._get_cache_path(model_id)
            if not cache_path.exists():
                return {"success": False, "error": "Model not found"}

            shutil.rmtree(cache_path)
            logger.info(f"Deleted model cache: {model_id}")
            return {"success": True}
        except Exception as e:
            logger.error(f"Failed to delete model {model_id}: {e}")
            return {"success": False, "error": str(e)}

    def verify_model(self, model_id: str, use_mirror: bool = True) -> Dict:
        """校验模型完整性（对比本地文件和远程文件列表）

        Args:
            model_id: 模型 ID
            use_mirror: 是否使用 hf-mirror 镜像

        Returns:
            {"valid": bool, "missing": [], "extra": []}
        """
        try:
            cache_path = self._get_cache_path(model_id)
            if not cache_path.exists():
                return {"valid": False, "missing": ["all"], "extra": []}

            # 获取远程文件列表
            endpoint = "https://hf-mirror.com" if use_mirror else None
            api = HfApi(endpoint=endpoint)
            remote_files = list(api.list_repo_tree(model_id, repo_type="model"))
            remote_file_names = {f.path for f in remote_files if hasattr(f, 'path') and not f.path.endswith('/')}

            # 获取本地文件列表（从 snapshots 目录）
            snapshots_dir = cache_path / "snapshots"
            local_file_names = set()
            if snapshots_dir.exists():
                for snapshot in snapshots_dir.iterdir():
                    if snapshot.is_dir():
                        for f in snapshot.rglob('*'):
                            if f.is_file():
                                rel_path = f.relative_to(snapshot)
                                local_file_names.add(str(rel_path))

            # 对比文件列表
            missing = list(remote_file_names - local_file_names)
            extra = list(local_file_names - remote_file_names)

            valid = len(missing) == 0
            return {"valid": valid, "missing": missing, "extra": extra}
        except Exception as e:
            logger.error(f"Failed to verify model {model_id}: {e}")
            return {"valid": False, "error": str(e), "missing": [], "extra": []}
