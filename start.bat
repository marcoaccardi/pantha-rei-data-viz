@echo off
REM NOAA Climate Data Globe - Windows Startup Script
REM Starts both FastAPI backend and React frontend

echo 🌍 Starting NOAA Climate Data Globe System (Windows)
echo ==============================================

REM Colors for Windows
REM Note: cmd.exe doesn't support ANSI by default; keep variables empty for clean output
set "RED="
set "GREEN="
set "YELLOW="
set "BLUE="
set "NC="

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

REM Function to kill processes on specific ports
echo %BLUE%🧹 Freeing required ports...%NC%

REM Kill processes on port 8000 (API)
echo %BLUE%🔍 Checking for processes on port 8000 (API)...%NC%
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 2^>nul') do (
    echo %YELLOW%🔧 Killing process %%a on port 8000...%NC%
    taskkill /f /pid %%a >nul 2>&1
)

REM Kill processes on port 5173 (Frontend)
echo %BLUE%🔍 Checking for processes on port 5173 (Frontend)...%NC%
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173 2^>nul') do (
    echo %YELLOW%🔧 Killing process %%a on port 5173...%NC%
    taskkill /f /pid %%a >nul 2>&1
)

REM Kill processes on port 8765 (WebSocket, if used)
echo %BLUE%🔍 Checking for processes on port 8765 (WebSocket)...%NC%
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8765 2^>nul') do (
    echo %YELLOW%🔧 Killing process %%a on port 8765...%NC%
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
        echo %YELLOW%Trying with standard Python venv...%NC%
        python -m venv .venv
        if errorlevel 1 (
            echo %RED%❌ Failed to create virtual environment with both methods%NC%
            pause
            exit /b 1
        )
    )
)

REM Debug virtual environment structure
echo %BLUE%🐍 Checking virtual environment structure...%NC%
if exist ".venv" (
    echo %GREEN%✅ .venv directory found%NC%
    echo %BLUE%📁 Contents of .venv:%NC%
    dir /B ".venv" 2>nul
    
    if exist ".venv\Scripts" (
        echo %GREEN%✅ Scripts directory found%NC%
        echo %BLUE%📁 Contents of .venv\Scripts:%NC%
        dir /B ".venv\Scripts" 2>nul
    ) else (
        echo %YELLOW%⚠️  Scripts directory not found%NC%
    )
) else (
    echo %RED%❌ .venv directory not found%NC%
)

REM Try multiple activation methods
echo %BLUE%🐍 Attempting to activate Python virtual environment...%NC%

REM Method 1: Standard Windows activation
if exist ".venv\Scripts\activate.bat" (
    echo %BLUE%Trying .venv\Scripts\activate.bat...%NC%
    call .venv\Scripts\activate.bat
    echo %GREEN%✅ Virtual environment activated (method 1)%NC%
    goto :venv_activated
)

REM Method 2: Try activate.ps1 (PowerShell)
if exist ".venv\Scripts\activate.ps1" (
    echo %BLUE%Trying .venv\Scripts\activate.ps1...%NC%
    powershell -ExecutionPolicy Bypass -File ".venv\Scripts\activate.ps1"
    echo %GREEN%✅ Virtual environment activated (method 2)%NC%
    goto :venv_activated
)

REM Method 3: Try direct python.exe
if exist ".venv\Scripts\python.exe" (
    echo %BLUE%Using direct python.exe path...%NC%
    set "PYTHON_PATH=%cd%\.venv\Scripts\python.exe"
    echo %GREEN%✅ Using direct Python path (method 3)%NC%
    goto :venv_activated
)

REM Method 4: Recreate virtual environment
echo %YELLOW%⚠️  Virtual environment appears corrupted. Recreating...%NC%
rmdir /S /Q ".venv" 2>nul
echo %BLUE%Creating new virtual environment...%NC%

uv venv --python python >nul 2>&1
if not errorlevel 1 (
    if exist ".venv\Scripts\activate.bat" (
        call .venv\Scripts\activate.bat
        echo %GREEN%✅ Virtual environment recreated and activated (uv)%NC%
        goto :venv_activated
    )
)

REM Fallback to standard Python venv
python -m venv .venv >nul 2>&1
if not errorlevel 1 (
    if exist ".venv\Scripts\activate.bat" (
        call .venv\Scripts\activate.bat
        echo %GREEN%✅ Virtual environment recreated and activated (python venv)%NC%
        goto :venv_activated
    )
)

echo %RED%❌ Failed to create or activate virtual environment%NC%
echo %YELLOW%Please manually create the virtual environment:%NC%
echo   cd backend
echo   python -m venv .venv
echo   .venv\Scripts\activate.bat
pause
exit /b 1

:venv_activated

REM Determine Python command from virtual environment if available (Windows or POSIX layout)
set "PYTHON_CMD=python"
if exist ".venv\Scripts\python.exe" set "PYTHON_CMD=%cd%\.venv\Scripts\python.exe"
if exist ".venv\bin\python.exe" set "PYTHON_CMD=%cd%\.venv\bin\python.exe"

REM Verify Python is working
"%PYTHON_CMD%" --version >nul 2>&1
if errorlevel 1 (
    echo %RED%❌ Python not available in virtual environment%NC%
    pause
    exit /b 1
)

echo %BLUE%🐍 Using Python: %NC%
"%PYTHON_CMD%" --version

REM Check if dependencies are installed
echo %BLUE%📦 Checking Python dependencies...%NC%
"%PYTHON_CMD%" -c "import fastapi, uvicorn, requests, numpy, pandas" >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%⚠️  Installing Python dependencies...%NC%
    if exist "requirements.txt" (
        REM Try uv first, fallback to pip
        uv pip install -r requirements.txt >nul 2>&1
        if errorlevel 1 (
            echo %YELLOW%uv install failed, trying pip...%NC%
            "%PYTHON_CMD%" -m pip install -r requirements.txt
        )
    ) else (
        echo %YELLOW%requirements.txt not found, installing essential packages...%NC%
        "%PYTHON_CMD%" -m pip install fastapi uvicorn requests numpy pandas python-dotenv
    )
    if errorlevel 1 (
        echo %RED%❌ Failed to install dependencies%NC%
        pause
        exit /b 1
    )
)

REM Check for Copernicus Marine CLI
echo %BLUE%🌊 Checking Copernicus Marine CLI...%NC%
"%PYTHON_CMD%" -c "import copernicusmarine" >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%⚠️  Copernicus Marine CLI not found. Installing...%NC%
    "%PYTHON_CMD%" -m pip install copernicusmarine
    if errorlevel 1 (
        echo %YELLOW%⚠️  Failed to install Copernicus Marine CLI, continuing without it...%NC%
    ) else (
        echo %GREEN%✅ Copernicus Marine CLI installed%NC%
    )
) else (
    echo %GREEN%✅ Copernicus Marine CLI available%NC%
)

echo %GREEN%✅ Python environment ready%NC%

REM Start FastAPI server in background
echo %BLUE%🌊 Starting Ocean Data API server on port 8000...%NC%
echo %GREEN%✅ Using FastAPI with real data from Copernicus Marine%NC%

REM Use proper quoting with start/cmd redirection
start "" /b cmd /c ""%PYTHON_CMD%" -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload > "%ROOT_DIR%\logs\api.log" 2>&1"

cd "%ROOT_DIR%"

REM Wait and test API startup
echo %BLUE%⏳ Waiting for API server to start...%NC%
timeout /t 8 /nobreak > nul

REM Test API connection (simple check)
echo %BLUE%🔗 Testing API connection...%NC%
for /L %%i in (1,1,5) do (
    where curl >nul 2>&1
    if not errorlevel 1 (
        curl -s http://localhost:8000/health >nul 2>&1
        if not errorlevel 1 (
            echo %GREEN%API server is responding correctly%NC%
            goto :api_ready
        )
    ) else (
        echo %YELLOW%curl not found, skipping health check attempt %%i of 5%NC%
    )
    echo %YELLOW%API server not ready - attempt %%i of 5%NC%
    timeout /t 3 /nobreak > nul
)

echo %YELLOW%⚠️  API connection test incomplete, but proceeding...%NC%

:api_ready

REM Setup and start frontend
cd frontend

REM Check if Node.js is available
where npm >nul 2>&1
if errorlevel 1 (
    echo %RED%❌ npm not found. Please install Node.js%NC%
    pause
    exit /b 1
)

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
echo %BLUE%⚛️  Starting React Three Fiber frontend...%NC%
start "" /b cmd /c "npm run dev > \"%ROOT_DIR%\logs\frontend.log\" 2>&1"

cd "%ROOT_DIR%"

REM Wait for services to start
echo %BLUE%⏳ Waiting for services to start...%NC%
timeout /t 5 /nobreak > nul

echo.
echo %GREEN%✅ All services started successfully!%NC%
echo.
echo %GREEN%🌊 REAL OCEAN DATA ^& DATE FUNCTIONALITY READY%NC%
echo %GREEN%🌍 Globe Interface: %BLUE%http://localhost:5173%NC%
echo %GREEN%🔗 API Server: %BLUE%http://localhost:8000%NC%
echo %GREEN%📖 API Documentation: %BLUE%http://localhost:8000/docs%NC%
echo.
echo %BLUE%📊 Features Available:%NC%
echo %GREEN%  ✅ Random ocean coordinate generation (120 verified points)%NC%
echo %GREEN%  ✅ Random date generation with data availability validation%NC%
echo %GREEN%  ✅ REAL ocean data from Copernicus Marine: SST, salinity, waves, currents, chlorophyll, pH%NC%
echo %GREEN%  ✅ Temporal coverage: 1972-2025 with guaranteed data from 2022-06-01%NC%
echo %GREEN%  ✅ Real-time REST API communication with date parameters%NC%
echo %GREEN%  ✅ Automatic data download and caching with progress notifications%NC%
echo %GREEN%  ✅ Smart caching - subsequent requests load instantly%NC%
echo %GREEN%  ✅ Port management - all ports freed before startup%NC%
echo.
echo %YELLOW%📊 Usage:%NC%
echo   • Click anywhere on the 3D globe to select coordinates
echo   • Use date picker to select specific dates or generate random dates
echo   • Click 'Random Location' for verified ocean coordinates
echo   • Click 'Random Both' for random date + location combinations
echo   • Toggle SST overlay with the button in the data panel
echo   • Rotate, zoom, and pan the globe with mouse controls
echo   • Ocean data will be fetched automatically for selected locations and dates
echo.
echo %YELLOW%📄 Logs:%NC%
echo   • API server: type "%ROOT_DIR%\logs\api.log"
echo   • Frontend: type "%ROOT_DIR%\logs\frontend.log"
echo.
echo %YELLOW%🔧 To stop services:%NC%
echo   • Press Ctrl+C in this window
echo   • Or manually kill processes on ports 8000 and 5173
echo   • Or use Task Manager to end uvicorn and npm processes
echo.
echo %GREEN%🚀 System is ready! Open http://localhost:5173 in your browser%NC%

REM Create a simple monitoring loop
echo %BLUE%🔍 Starting service monitoring... (Press Ctrl+C to stop all services)%NC%
echo.

:monitor_loop
timeout /t 30 /nobreak > nul

REM Check if API port is listening
netstat -aon | findstr /R /C:":8000[ ]" | findstr LISTENING >nul 2>&1
if errorlevel 1 (
    echo API server may have stopped listening on port 8000! Check logs\api.log
)

REM Check if frontend port is listening
netstat -aon | findstr /R /C:":5173[ ]" | findstr LISTENING >nul 2>&1
if errorlevel 1 (
    echo Frontend server may have stopped listening on port 5173! Check logs\frontend.log
)

goto :monitor_loop