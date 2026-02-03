# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Vocistant Backend
Target: macOS arm64 (Apple Silicon)
"""

import sys
from pathlib import Path

block_cipher = None

# Project paths
BACKEND_DIR = Path(SPECPATH)
PROJECT_ROOT = BACKEND_DIR.parent

a = Analysis(
    ['main.py'],
    pathex=[str(BACKEND_DIR)],
    binaries=[],
    datas=[],
    hiddenimports=[
        # MLX and audio processing
        'mlx',
        'mlx.core',
        'mlx.nn',
        'mlx_audio',
        'mlx_audio.transcribe',
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
        'anyio',
        # Hugging Face
        'huggingface_hub',
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
