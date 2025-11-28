# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

block_cipher = None

# 프로젝트 루트 경로 (spec 파일 위치 기준)
spec_root = os.path.abspath(SPECPATH)
project_root = os.path.dirname(spec_root)

# resources 폴더가 있을 때만 포함
datas = []
resources_path = os.path.join(project_root, 'resources')
if os.path.exists(resources_path):
    datas.append((resources_path, 'resources'))

# hiddenimports에 src 패키지 추가
hiddenimports = [
    'yt_dlp',
    'qasync',
    'src',
    'src.core',
    'src.core.config',
    'src.core.downloader',
    'src.gui',
    'src.gui.main_window',
    'src.gui.settings_dialog',
    'src.utils',
]

a = Analysis(
    [os.path.join(project_root, 'run.py')],
    pathex=[project_root],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
