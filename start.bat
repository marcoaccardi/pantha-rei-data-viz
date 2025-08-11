@echo off
REM NOAA Climate Data Globe - Windows Startup Script
REM Starts both FastAPI backend and React frontend

echo 🌍 Starting NOAA Climate Data Globe System (Windows)
echo ==============================================

REM Colors for Windows (limited support)
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "NC=[0m"

REM Store the root directory
set ROOT_DIR=%cd%

REM Check if required directories exist
if not exist "backend" (
    echo %RED%❌ backend directory not found%NC%
    pause
    exit /b 1
)

if not exist "frontend" (
    echo %RED%❌ frontend directory not found%NC%
    pause
    exit /b 1
)

REM Create logs directory if it doesn't exist
if not exist "logs" (
    echo %BLUE%📁 Creating logs directory...%NC%
    mkdir logs
)

REM Function to check and kill processes on ports
echo %BLUE%🧹 Checking for existing processes on required ports...%NC%

REM Kill processes on port 8000 (API)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do (
    echo %YELLOW%🔧 Killing process on port 8000...%NC%
    taskkill /f /pid %%a >nul 2>&1
)

REM Kill processes on port 5173 (Frontend)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173') do (
    echo %YELLOW%🔧 Killing process on port 5173...%NC%
    taskkill /f /pid %%a >nul 2>&1
)

echo %GREEN%✅ Ports freed%NC%

REM Setup backend Python environment
cd backend

REM Check if virtual environment exists
if not exist ".venv" (
    echo %YELLOW%⚠️  Backend .venv not found, creating with uv...%NC%
    uv venv --python python
    if errorlevel 1 (
        echo %RED%❌ Failed to create virtual environment%NC%
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo %BLUE%🐍 Activating Python virtual environment...%NC%
call .venv\Scripts\activate.bat

REM Check if dependencies are installed
echo %BLUE%📦 Checking Python dependencies...%NC%
python -c "import fastapi, uvicorn, requests, numpy, pandas" >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%⚠️  Installing Python dependencies...%NC%
    uv pip install -r requirements.txt
    if errorlevel 1 (
        echo %RED%❌ Failed to install dependencies%NC%
        pause
        exit /b 1
    )
)

echo %GREEN%✅ Python environment ready%NC%

REM Start FastAPI server in background
echo %BLUE%🌊 Starting FastAPI server...%NC%
start /b python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload > "%ROOT_DIR%\logs\api.log" 2>&1

cd "%ROOT_DIR%"

REM Setup and start frontend
cd frontend

REM Check if node_modules exists
if not exist "node_modules" (
    echo %BLUE%📦 Installing frontend dependencies...%NC%
    npm install
    if errorlevel 1 (
        echo %RED%❌ Failed to install frontend dependencies%NC%
        pause
        exit /b 1
    )
)

REM Start frontend development server in background
echo %BLUE%⚛️  Starting React development server...%NC%
start /b npm run dev > "%ROOT_DIR%\logs\frontend.log" 2>&1

cd "%ROOT_DIR%"

REM Wait for services to start
echo %BLUE%⏳ Waiting for services to start...%NC%
timeout /t 8 /nobreak > nul

echo.
echo %GREEN%✅ All services started successfully!%NC%
echo.
echo %GREEN%🌊 REAL OCEAN DATA ^& DATE FUNCTIONALITY READY%NC%
echo %GREEN%🌍 Globe Interface: %BLUE%http://localhost:5173%NC%
echo %GREEN%🔗 API Server: %BLUE%http://localhost:8000%NC%
echo %GREEN%📖 API Documentation: %BLUE%http://localhost:8000/docs%NC%
echo.
echo %BLUE%📊 Features Available:%NC%
echo %GREEN%  ✅ Random ocean coordinate generation%NC%
echo %GREEN%  ✅ Random date generation with data availability validation%NC%
echo %GREEN%  ✅ REAL ocean data from Copernicus Marine%NC%
echo %GREEN%  ✅ Temporal coverage: 1972-2025%NC%
echo %GREEN%  ✅ Real-time REST API communication%NC%
echo.
echo %YELLOW%📄 Logs:%NC%
echo   • API server: type logs\api.log
echo   • Frontend: type logs\frontend.log
echo.
echo %YELLOW%🔧 To stop services:%NC%
echo   • Press Ctrl+C in this window
echo   • Or manually kill processes on ports 8000 and 5173
echo.
echo %GREEN%🚀 System is ready! Open http://localhost:5173 in your browser%NC%

pause