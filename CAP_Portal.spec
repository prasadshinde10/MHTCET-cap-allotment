# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# Project root directory
BASE_DIR = os.path.abspath(SPECPATH)

datas = [
    (os.path.join(BASE_DIR, 'frontend', 'dist'), os.path.join('frontend', 'dist')),
    (os.path.join(BASE_DIR, '.env.example'), '.'),
]

# Include SQLite database files from backend/ or root
for db_name in ['cutoff.db', 'csab.db', 'josaa.db', 'medical.db', 'iiser.db']:
    backend_db = os.path.join(BASE_DIR, 'backend', db_name)
    root_db = os.path.join(BASE_DIR, db_name)
    if os.path.exists(backend_db):
        datas.append((backend_db, 'backend'))
        datas.append((backend_db, '.'))
    elif os.path.exists(root_db):
        datas.append((root_db, 'backend'))
        datas.append((root_db, '.'))

hidden_imports = [
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespans',
    'uvicorn.lifespans.on',
    'uvicorn.lifespans.off',
    'fastapi',
    'fastapi.staticfiles',
    'fastapi.responses',
    'starlette',
    'starlette.staticfiles',
    'starlette.responses',
    'starlette.routing',
    'pydantic',
    'pydantic_settings',
    'sqlalchemy',
    'sqlalchemy.dialects.sqlite',
    'slowapi',
    'passlib',
    'passlib.handlers.bcrypt',
    'bcrypt',
    'jwt',
    'multipart',
    'email_validator',
    'bs4',
    'lxml',
    'requests',
]

# Collect all submodules of app
hidden_imports += collect_submodules('app')

a = Analysis(
    ['desktop_app.py'],
    pathex=[BASE_DIR, os.path.join(BASE_DIR, 'backend')],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'IPython', 'notebook', 'torch', 'scipy'],
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
    name='CAP_Portal',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
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
    name='CAP_Portal',
)
