# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

block_cipher = None

# resources 폴더가 있을 때만 포함
datas = []
resources_path = Path('../resources')
if resources_path.exists():
    datas.append(('../resources', 'resources'))

a = Analysis(
    ['../src/main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['yt_dlp', 'qasync'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='VideoDownloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='VideoDownloader',
)
