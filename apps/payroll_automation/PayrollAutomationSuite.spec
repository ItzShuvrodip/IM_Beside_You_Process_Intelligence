# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:/IMBY/apps/payroll_automation/desktop_app.py'],
    pathex=[],
    binaries=[],
    datas=[('D:/IMBY/apps/payroll_automation/frontend', 'apps/payroll_automation/frontend'), ('D:/IMBY/apps/payroll_automation/sample_data', 'apps/payroll_automation/sample_data'), ('D:/IMBY/src', 'src')],
    hiddenimports=['uvicorn', 'uvicorn.logging', 'uvicorn.loops.auto', 'uvicorn.protocols.http.auto', 'uvicorn.lifespan.on', 'fastapi', 'starlette', 'pydantic', 'pydantic_core', 'webview', 'webview.platforms.winforms', 'webview.platforms.edgechromium', 'pythonnet', 'clr_loader'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PayrollAutomationSuite',
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
    name='PayrollAutomationSuite',
)
