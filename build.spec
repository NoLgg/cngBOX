# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置 — 草泥鸽工具箱。

用法：
    pyinstaller build.spec

产物：dist/草泥鸽工具箱.exe（单文件、无控制台窗口）
"""

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# 资源打包：assets 目录随 exe 内嵌（_MEIPASS/assets）
_assets = Path("assets")
datas = [
    (str(_assets / "icons"), "assets/icons"),
    (str(_assets / "icon-app.ico"), "assets"),
]
binaries = []
hiddenimports = collect_submodules("cng_toolbox")

a = Analysis(
    ["src/cng_toolbox/main.py"],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.Qt3DCore",
        "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
        "PySide6.QtMultimedia",
        "PySide6.QtPdf",
        "PySide6.QtBluetooth",
        "PySide6.QtNfc",
        "PySide6.QtPositioning",
        "PySide6.QtSensors",
        "PySide6.QtSerialPort",
        "PySide6.QtSql",
        "PySide6.QtTest",
        "PySide6.QtXml",
        "tkinter",
        "unittest",
        "pydoc",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# exe 图标（应用图标）
_ico = str(_assets / "icon-app.ico")

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="草泥鸽工具箱",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=_ico,
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
    upx=False,
    upx_exclude=[],
    name="草泥鸽工具箱",
)

# 单文件模式（--onefile）
if os.environ.get("CNG_ONEFILE"):
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name="草泥鸽工具箱",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        icon=_ico,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
