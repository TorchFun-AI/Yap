# PyInstaller hook for silero-vad
from PyInstaller.utils.hooks import collect_all, collect_data_files

datas, binaries, hiddenimports = collect_all('silero_vad')
datas += collect_data_files('silero_vad')

# silero-vad depends on torch
hiddenimports += [
    'torch',
    'torchaudio',
]
