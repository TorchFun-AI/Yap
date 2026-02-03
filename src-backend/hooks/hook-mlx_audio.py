# PyInstaller hook for mlx_audio
from PyInstaller.utils.hooks import collect_all, collect_submodules

datas, binaries, hiddenimports = collect_all('mlx_audio')
hiddenimports += collect_submodules('mlx_audio')
