# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Vocistant Backend
Target: macOS arm64 (Apple Silicon)
"""

import os
import site
import sys
from pathlib import Path

block_cipher = None

# Project paths
BACKEND_DIR = Path(SPECPATH)
PROJECT_ROOT = BACKEND_DIR.parent

# MLX metallib path - needed for Metal GPU acceleration
# MLX looks for mlx.metallib in the same directory as the executable
site_packages = site.getsitepackages()[0]
mlx_metallib = os.path.join(site_packages, 'mlx', 'lib', 'mlx.metallib')

a = Analysis(
    ['main.py'],
    pathex=[str(BACKEND_DIR)],
    binaries=[],
    datas=[
        (mlx_metallib, '.'),  # Copy mlx.metallib to executable directory
    ],
    hiddenimports=[
        # MLX and audio processing
        'mlx',
        'mlx.core',
        'mlx.nn',
        'mlx_audio',
        'mlx_audio.transcribe',
        # mlx_audio 模型子模块 (PyInstaller 静态导入支持)
        'mlx_audio.stt',
        'mlx_audio.stt.models',
        'mlx_audio.stt.models.whisper',
        'mlx_audio.stt.models.funasr',
        # Silero VAD
        'silero_vad',
        # PyTorch (required by silero-vad)
        'torch',
        'torchaudio',
        # FastAPI and dependencies
        'fastapi',
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'starlette',
        'pydantic',
        'pydantic_core',
        # Audio
        'sounddevice',
        'numpy',
        # HTTP client
        'httpx',
        'httpcore',
        'anyio',
        # Hugging Face 子模块
        'huggingface_hub',
        'huggingface_hub.hf_api',
        'huggingface_hub.file_download',
        'huggingface_hub._snapshot_download',
        'huggingface_hub.utils',
        'filelock',
        # OpenAI 客户端
        'openai',
        'openai._client',
        # macOS 框架
        'Quartz',
        'Quartz.CoreGraphics',
        'objc',
        'Foundation',
        # Other
        'tiktoken',
        'tiktoken_ext',
        'tiktoken_ext.openai_public',
        'regex',
    ],
    hookspath=['hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'PIL',
        'cv2',
        'scipy.spatial.cKDTree',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='vocistant-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='arm64',
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='vocistant-backend',
)
