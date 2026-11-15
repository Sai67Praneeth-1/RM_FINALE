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

REM 2. Check Node & Hugging Face Router
echo.
echo [2/4] Checking LLM Engine & Frontend runtime...
echo [INFO] Primary LLM Engine: Hugging Face Router (router.huggingface.co/v1)
echo [INFO] Active Models: meta-llama/Llama-3.1-8B-Instruct & Qwen/Qwen2.5-7B-Instruct
where npm >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] npm is not found in PATH. Please install Node.js for React frontend.
)

REM 3. Start FastAPI Backend in background
echo.
echo [3/4] Starting FastAPI Observability API Server on http://127.0.0.1:8000...
start "Transparency API Server" cmd /k "python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000"

timeout /t 3 /nobreak >nul

REM 4. Start Primary React High-Speed Frontend
echo [4/4] Starting Primary React Frontend on http://127.0.0.1:5173...
start "React Frontend (Primary)" cmd /k "cd frontend && npm run dev -- --host 127.0.0.1 --port 5173"

REM Optional Secondary Streamlit Dashboard
echo.
echo [INFO] Streamlit Research Dashboard available as secondary at http://127.0.0.1:8501
start "Streamlit Dashboard (Secondary)" cmd /k "streamlit run dashboard/app.py --server.port 8501 --server.headless false"

timeout /t 2 /nobreak >nul
start http://localhost:5173

echo.
echo ================================================================================
echo  APPLICATION SUCCESSFULLY LAUNCHED!
echo  - PRIMARY UI (React):       http://127.0.0.1:5173  (Opened in browser)
echo  - Secondary UI (Streamlit): http://127.0.0.1:8501
echo  - Backend API Docs:         http://127.0.0.1:8000/docs
echo ================================================================================
echo.
echo Press any key to exit this launcher window (services will remain running).
pause >nul

