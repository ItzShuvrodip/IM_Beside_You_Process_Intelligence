@echo off
REM =========================================================================
REM IMBY ENTERPRISE PAYROLL DEDUCTION AUTOMATION SUITE
REM Standalone Desktop Application Launcher (Native Windows Window)
REM =========================================================================
title IMBY Enterprise Payroll Deduction Automation Suite

set APP_DIR=%~dp0
cd /d "%APP_DIR%"

if exist "%APP_DIR%dist\PayrollAutomationSuite\PayrollAutomationSuite.exe" (
    echo Launching Compiled Desktop Executable...
    start "" "%APP_DIR%dist\PayrollAutomationSuite\PayrollAutomationSuite.exe"
    exit /b 0
)

echo Launching Python Desktop Container...
python desktop_app.py
pause
