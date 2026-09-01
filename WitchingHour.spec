# PyInstaller spec. Run from this folder:
#   pyinstaller WitchingHour.spec

import os
import sys

sys.path.insert(0, os.path.abspath("."))

from app.version import APP_NAME, COMPANY, COPYRIGHT, EXE_NAME, VERSION, VERSION_TUPLE
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VarFileInfo,
    VarStruct,
    VSVersionInfo,
)

block_cipher = None
icon_file = "assets/app.ico"
icon_arg = icon_file if os.path.isfile(icon_file) else None

datas = []
if os.path.isdir("assets"):
    datas.append(("assets", "assets"))

version_info = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=VERSION_TUPLE,
        prodvers=VERSION_TUPLE,
        mask=0x3F,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0),
    ),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    "040904B0",
                    [
                        StringStruct("CompanyName", COMPANY),
                        StringStruct("FileDescription", APP_NAME),
                        StringStruct("FileVersion", VERSION),
                        StringStruct("InternalName", EXE_NAME),
                        StringStruct("OriginalFilename", f"{EXE_NAME}.exe"),
                        StringStruct("ProductName", APP_NAME),
                        StringStruct("ProductVersion", VERSION),
                        StringStruct("LegalCopyright", COPYRIGHT),
                    ],
                )
            ]
        ),
        VarFileInfo([VarStruct("Translation", [1033, 1200])]),
    ],
)

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
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
    name=EXE_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=icon_arg,
    version=version_info,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name=EXE_NAME,
)