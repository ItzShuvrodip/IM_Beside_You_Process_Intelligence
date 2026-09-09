@echo off
REM =========================================================================
REM IMBY Enterprise Payroll Deduction Automation Suite - One-Click Launcher
REM =========================================================================

title IMBY Payroll Deduction Automation Suite
cd /d "%~dp0..\.."

echo =========================================================================
echo   Starting IMBY Payroll Deduction Automation Suite
echo   Port: 8500 | Standalone Desktop/Web Mode
echo =========================================================================

if exist "C:\Users\Sentinel\miniconda3\envs\nlp\python.exe" (
    "C:\Users\Sentinel\miniconda3\envs\nlp\python.exe" apps\payroll_automation\run_app.py
) else (
    python apps\payroll_automation\run_app.py
)

pause
