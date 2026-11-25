@echo off
setlocal
cd /d "%~dp0"
if exist "venv\Scripts\python.exe" (
  venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8502
) else (
  python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8502
)
pause
