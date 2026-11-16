# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

root = Path(SPECPATH).resolve().parent.parent

datas = [
    (str(root / 'templates'), 'templates'),
    (str(root / 'static'), 'static'),
    (str(root / 'public'), 'public'),
]
datas += collect_data_files('reportlab')

analysis = Analysis(
    ['app.py'],
    pathex=[str(root)],
    binaries=[],
    datas=datas,
    hiddenimports=['reportlab', 'openpyxl'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name='SIGCEM',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)
