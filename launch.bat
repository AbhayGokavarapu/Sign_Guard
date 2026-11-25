@echo off
title SignGuard — Forensic Dashboard
cd /d "%~dp0"

echo.
echo  ==========================================
echo   SignGuard ^| Document Forensics Platform
echo  ==========================================
echo.

REM Kill any old streamlit processes on port 8502
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8502 " 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo  Starting dashboard on http://localhost:8502
echo  Press Ctrl+C in this window to stop.
echo.

call venv\Scripts\activate
venv\Scripts\streamlit.exe run app.py

pause
