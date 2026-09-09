"""
Build script to compile the Standalone Enterprise Payroll Automation Suite
into an independent Windows desktop executable (.exe) using PyInstaller.
"""

import sys
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
APP_DIR = ROOT / "apps" / "payroll_automation"
ENTRY_POINT = APP_DIR / "desktop_app.py"
DIST_DIR = APP_DIR / "dist"
BUILD_DIR = APP_DIR / "build"
SPEC_FILE = APP_DIR / "PayrollAutomationSuite.spec"

print("=" * 76)
print(" COMPILING STANDALONE ENTERPRISE PAYROLL AUTOMATION SUITE (.EXE)")
print("=" * 76)
print(f" Source root:   {ROOT}")
print(f" Entry point:   {ENTRY_POINT}")
print(f" Target output: {DIST_DIR / 'PayrollAutomationSuite' / 'PayrollAutomationSuite.exe'}")
print("=" * 76)

frontend_dir = APP_DIR / "frontend"
sample_data_dir = APP_DIR / "sample_data"
src_dir = ROOT / "src"

# Assemble PyInstaller command
cmd = [
    sys.executable,
    "-m", "PyInstaller",
    "--noconfirm",
    "--onedir",
    "--windowed",
    "--name", "PayrollAutomationSuite",
    f"--distpath={DIST_DIR}",
    f"--workpath={BUILD_DIR}",
    f"--specpath={APP_DIR}",
    f"--add-data={frontend_dir};apps/payroll_automation/frontend",
    f"--add-data={sample_data_dir};apps/payroll_automation/sample_data",
    f"--add-data={src_dir};src",
    "--hidden-import=uvicorn",
    "--hidden-import=uvicorn.logging",
    "--hidden-import=uvicorn.loops.auto",
    "--hidden-import=uvicorn.protocols.http.auto",
    "--hidden-import=uvicorn.lifespan.on",
    "--hidden-import=fastapi",
    "--hidden-import=starlette",
    "--hidden-import=pydantic",
    "--hidden-import=pydantic_core",
    "--hidden-import=webview",
    "--hidden-import=webview.platforms.winforms",
    "--hidden-import=webview.platforms.edgechromium",
    "--hidden-import=pythonnet",
    "--hidden-import=clr_loader",
    str(ENTRY_POINT)
]

print("Executing build command:\n", " ".join(cmd), "\n")
res = subprocess.run(cmd, cwd=str(ROOT))

if res.returncode == 0:
    exe_path = DIST_DIR / "PayrollAutomationSuite" / "PayrollAutomationSuite.exe"
    print("\n" + "=" * 76)
    print(f" [OK] BUILD SUCCESSFUL! Executable generated at:")
    print(f"      {exe_path}")
    print("=" * 76)
else:
    print(f"\n[ERROR] Build failed with exit code {res.returncode}")
    sys.exit(res.returncode)
