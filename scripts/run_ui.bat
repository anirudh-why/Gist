@echo off
REM Launch Streamlit using the project's virtual environment on Windows (cmd)
setlocal enableextensions
set ROOT_DIR=%~dp0..

if exist "%ROOT_DIR%\.venv\Scripts\python.exe" (
  "%ROOT_DIR%\.venv\Scripts\python.exe" -m streamlit run "%ROOT_DIR%\app.py" %*
) else (
  python -m streamlit run "%ROOT_DIR%\app.py" %*
)
