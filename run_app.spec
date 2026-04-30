# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

# 1. 로컬 리소스 정의
datas = [('app.py', '.'), ('core', 'core'), ('agents', 'agents'), ('prompts', 'prompts')]
binaries = []
hiddenimports = []

# 2. 필수 라이브러리 (requirements.txt 기반 모든 의존성 강제 포함)
essential_packages = [
    'streamlit',
    'google.genai',
    'langgraph',
    'webview',       # pywebview
    'pdfplumber',
    'dotenv',        # python-dotenv
    'clr',           # pythonnet
    'edge_tts',
    'aiohttp'
]

for pkg in essential_packages:
    try:
        tmp_ret = collect_all(pkg)
        datas += tmp_ret[0]
        binaries += tmp_ret[1]
        hiddenimports += tmp_ret[2]
    except Exception as e:
        print(f"Warning: Could not collect all for {pkg}: {e}")

# 3. 분석 및 빌드 설정
a = Analysis(
    ['run_app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'notebook'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AI_Interview_Auto',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
