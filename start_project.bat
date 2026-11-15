@echo off
setlocal enabledelayedexpansion

echo ================================================================================
echo  TRANSPARENCY & OPENNESS IN AGENTIC AI SYSTEMS
echo  Multi-Agent Observability Gateway & Three-Graph Research Platform
echo ================================================================================
echo.

cd /d "%~dp0"
set "PYTHONPATH=%~dp0;%PYTHONPATH%"

REM 1. Check Python
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not found in PATH! Please install Python 3.10+ and re-run.
    pause
    exit /b 1
)

echo [1/4] Checking Python environment...
python -c "import sys; print('Using Python:', sys.version.split()[0], 'at', sys.executable)"

REM 2. Check Ollama
echo.
echo [2/4] Checking local Ollama service...
curl -s http://127.0.0.1:11434/api/tags >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [INFO] Ollama is online! Live LLM inference is enabled.
) else (
    echo [NOTICE] Ollama is not detected at http://127.0.0.1:11434.
    echo [NOTICE] The system will automatically run in Deterministic Demonstration Mode.
    echo.
    echo To install and run Ollama on Windows:
    echo   1. Download Ollama from: https://ollama.com/download/windows
    echo   2. Run the installer and launch Ollama.
    echo   3. Pull the recommended model: ollama pull qwen2.5:3b
    echo.
)

REM 3. Start FastAPI Backend in background
echo [3/4] Starting FastAPI Observability API Server on http://127.0.0.1:8000...
start "Transparency API Server" cmd /k "python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000"

timeout /t 3 /nobreak >nul

REM 4. Start High-Speed React Frontend
echo [4/5] Starting High-Speed React Frontend on http://127.0.0.1:5173...
start "React Frontend" cmd /k "cd frontend && npm run dev -- --host 127.0.0.1 --port 5173"

REM 5. Start Streamlit Dashboard (Secondary)
echo [5/5] Starting Streamlit Research Dashboard on http://127.0.0.1:8501...
start "Transparency Dashboard" cmd /k "streamlit run dashboard/app.py --server.port 8501 --server.headless false"

timeout /t 2 /nobreak >nul
start http://localhost:5173

echo.
echo ================================================================================
echo  APPLICATION SUCCESSFULLY LAUNCHED!
echo  - React High-Speed UI:  http://127.0.0.1:5173
echo  - Streamlit Dashboard:  http://127.0.0.1:8501
echo  - Backend API Docs:     http://127.0.0.1:8000/docs
echo ================================================================================
echo.
echo Press any key to exit this launcher window (services will remain running).
pause >nul

