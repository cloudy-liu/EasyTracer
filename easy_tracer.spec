# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# NOTE:
# - Do NOT copy `external/systrace` as raw source into dist.
#   Systrace is executed as a normal Python package module and is archived into PYZ.
# - Keep Simpleperf's external scripts on-disk for now (it uses file-path execution).

SPEC_PATH = Path(globals().get("__file__", Path.cwd() / "easy_tracer.spec")).resolve()
ROOT_DIR = SPEC_PATH.parent
APP_ICON_PATH = ROOT_DIR / "src" / "easy_tracer" / "assets" / "icons" / "app.ico"

datas = []
# Keep simpleperf external scripts available as files (path-based runner).
datas += [
    ("src/easy_tracer/framework/external/simpleperf", "easy_tracer/framework/external/simpleperf"),
]
# Include systrace HTML assets required by importlib.resources-based loader.
datas += collect_data_files(
    "easy_tracer.framework.external.systrace",
    includes=["*.html"],
)
# Include icon assets for navigation and app icon.
datas += [
    ("src/easy_tracer/assets/icons", "easy_tracer/assets/icons"),
]
binaries = []
PYSIDE6_KEEP = {
    "PySide6",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtSvg",
    "PySide6.QtWidgets",
    "PySide6.support",
    "PySide6.support.deprecated",
}
hiddenimports = sorted(
    module for module in PYSIDE6_KEEP if module not in {"PySide6", "PySide6.support"}
)
PYSIDE6_EXCLUDES = sorted(
    module for module in collect_submodules("PySide6") if module not in PYSIDE6_KEEP
)


a = Analysis(
    ['src/easy_tracer/main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=PYSIDE6_EXCLUDES + ['tkinter'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='easy_tracer',
    icon=str(APP_ICON_PATH),
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
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='easy_tracer',
)
