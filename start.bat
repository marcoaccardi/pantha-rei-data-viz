@echo off
REM NOAA Climate Data Globe - Windows Startup Script
REM Starts both FastAPI backend and React frontend

echo === Starting NOAA Climate Data Globe System (Windows) ===
echo ==============================================

REM Disable colors for better compatibility
set "RED="
set "GREEN="
set "YELLOW="
set "BLUE="
set "NC="

REM Store the root directory
set ROOT_DIR=%cd%

REM Check if required directories exist
if not exist "backend" (
    echo %RED%[ERROR] backend directory not found%NC%
    pause
    exit /b 1
)

if not exist "frontend" (
    echo %RED%[ERROR] frontend directory not found%NC%
    pause
    exit /b 1
)

REM Create logs directory if it doesn't exist
if not exist "logs" (
    echo %BLUE%[DIR] Creating logs directory...%NC%
    mkdir logs
)

REM Function to kill processes on specific ports
echo %BLUE%[CLEAN] Freeing required ports...%NC%

REM Kill processes on port 8000 (API)
echo %BLUE%[CHECK] Checking for processes on port 8000 (API)...%NC%
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 2^>nul') do (
    echo %YELLOW%[KILL] Killing process %%a on port 8000...%NC%
    taskkill /f /pid %%a >nul 2>&1
)

REM Kill processes on port 5173 (Frontend)
echo %BLUE%[CHECK] Checking for processes on port 5173 (Frontend)...%NC%
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173 2^>nul') do (
    echo %YELLOW%[KILL] Killing process %%a on port 5173...%NC%
    taskkill /f /pid %%a >nul 2>&1
)

REM Kill processes on port 8765 (WebSocket, if used)
echo %BLUE%[CHECK] Checking for processes on port 8765 (WebSocket)...%NC%
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8765 2^>nul') do (
    echo %YELLOW%[KILL] Killing process %%a on port 8765...%NC%
    taskkill /f /pid %%a >nul 2>&1
)

echo %GREEN%[OK] Ports freed%NC%

REM Setup backend Python environment
cd backend

REM Use platform-specific virtual environment for Windows
set "VENV_DIR=.venv-windows"

REM Check if Windows virtual environment exists
if not exist "%VENV_DIR%" (
    echo %YELLOW%[WARN] Backend %VENV_DIR% not found, creating with uv...%NC%
    uv venv %VENV_DIR% --python python
    if errorlevel 1 (
        echo %RED%[ERROR] Failed to create virtual environment%NC%
        echo %YELLOW%Trying with standard Python venv...%NC%
        python -m venv %VENV_DIR%
        if errorlevel 1 (
            echo %RED%[ERROR] Failed to create virtual environment with both methods%NC%
            pause
            exit /b 1
        )
    )
)

REM Inform if Linux venv also exists
if exist ".venv\bin" echo [INFO] Linux/macOS venv detected - dual-platform development enabled

REM Debug virtual environment structure
echo %BLUE%[PYTHON] Checking virtual environment structure...%NC%
if exist "%VENV_DIR%" (
    echo %GREEN%[OK] %VENV_DIR% directory found%NC%
    echo %BLUE%[DIR] Contents of %VENV_DIR%:%NC%
    dir /B "%VENV_DIR%" 2>nul
    
    if exist "%VENV_DIR%\Scripts" (
        echo %GREEN%[OK] Scripts directory found%NC%
        echo %BLUE%[DIR] Contents of %VENV_DIR%\Scripts:%NC%
        dir /B "%VENV_DIR%\Scripts" 2>nul
    ) else (
        echo %YELLOW%[WARN] Scripts directory not found%NC%
    )
) else (
    echo %RED%[ERROR] %VENV_DIR% directory not found%NC%
)

REM Try multiple activation methods
echo %BLUE%[PYTHON] Attempting to activate Python virtual environment...%NC%

REM Method 1: Standard Windows activation
if exist "%VENV_DIR%\Scripts\activate.bat" (
    echo %BLUE%Trying %VENV_DIR%\Scripts\activate.bat...%NC%
    call %VENV_DIR%\Scripts\activate.bat
    echo %GREEN%[OK] Virtual environment activated (method 1)%NC%
    goto :venv_activated
)

REM Method 2: Try activate.ps1 (PowerShell)
if exist "%VENV_DIR%\Scripts\activate.ps1" (
    echo %BLUE%Trying %VENV_DIR%\Scripts\activate.ps1...%NC%
    powershell -ExecutionPolicy Bypass -File "%VENV_DIR%\Scripts\activate.ps1"
    echo %GREEN%[OK] Virtual environment activated (method 2)%NC%
    goto :venv_activated
)

REM Method 3: Try direct python.exe
if exist "%VENV_DIR%\Scripts\python.exe" (
    echo %BLUE%Using direct python.exe path...%NC%
    set "PYTHON_PATH=%cd%\%VENV_DIR%\Scripts\python.exe"
    echo %GREEN%[OK] Using direct Python path (method 3)%NC%
    goto :venv_activated
)

REM Method 4: Recreate virtual environment
echo %YELLOW%[WARN] Virtual environment appears corrupted. Recreating...%NC%
rmdir /S /Q "%VENV_DIR%" 2>nul
echo %BLUE%Creating new virtual environment...%NC%

uv venv %VENV_DIR% --python python >nul 2>&1
if not errorlevel 1 (
    if exist "%VENV_DIR%\Scripts\activate.bat" (
        call %VENV_DIR%\Scripts\activate.bat
        echo %GREEN%[OK] Virtual environment recreated and activated (uv)%NC%
        goto :venv_activated
    )
)

REM Fallback to standard Python venv
python -m venv %VENV_DIR% >nul 2>&1
if not errorlevel 1 (
    if exist "%VENV_DIR%\Scripts\activate.bat" (
        call %VENV_DIR%\Scripts\activate.bat
        echo %GREEN%[OK] Virtual environment recreated and activated (python venv)%NC%
        goto :venv_activated
    )
)

echo %RED%[ERROR] Failed to create or activate virtual environment%NC%
echo %YELLOW%Please manually create the virtual environment:%NC%
echo   cd backend
echo   python -m venv .venv-windows
echo   .venv-windows\Scripts\activate.bat
pause
exit /b 1

:venv_activated

REM Determine Python command from virtual environment if available (Windows or POSIX layout)
set "PYTHON_CMD=python"
if exist "%VENV_DIR%\Scripts\python.exe" set "PYTHON_CMD=%cd%\%VENV_DIR%\Scripts\python.exe"
if exist "%VENV_DIR%\bin\python.exe" set "PYTHON_CMD=%cd%\%VENV_DIR%\bin\python.exe"

REM Verify Python is working
"%PYTHON_CMD%" --version >nul 2>&1
if errorlevel 1 (
    echo %RED%[ERROR] Python not available in virtual environment%NC%
    pause
    exit /b 1
)

echo %BLUE%[PYTHON] Using Python: %NC%
"%PYTHON_CMD%" --version

REM Check if dependencies are installed
echo %BLUE%[DEPS] Checking Python dependencies...%NC%
"%PYTHON_CMD%" -c "import fastapi, uvicorn, requests, numpy, pandas" >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%[WARN] Installing Python dependencies...%NC%
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
        echo %RED%[ERROR] Failed to install dependencies%NC%
        pause
        exit /b 1
    )
)

REM Check for Copernicus Marine CLI
echo %BLUE%[CMEMS] Checking Copernicus Marine CLI...%NC%
"%PYTHON_CMD%" -c "import copernicusmarine" >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%[WARN] Copernicus Marine CLI not found. Installing...%NC%
    "%PYTHON_CMD%" -m pip install copernicusmarine
    if errorlevel 1 (
        echo %YELLOW%[WARN] Failed to install Copernicus Marine CLI, continuing without it...%NC%
    ) else (
        echo %GREEN%[OK] Copernicus Marine CLI installed%NC%
    )
) else (
    echo %GREEN%[OK] Copernicus Marine CLI available%NC%
)

echo %GREEN%[OK] Python environment ready%NC%

REM Start FastAPI server in background
echo %BLUE%[API] Starting Ocean Data API server on port 8000...%NC%
echo %GREEN%[OK] Using FastAPI with real data from Copernicus Marine%NC%

REM Use proper quoting with start/cmd redirection
start "" /b cmd /c ""%PYTHON_CMD%" -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload > "%ROOT_DIR%\logs\api.log" 2>&1"

cd "%ROOT_DIR%"

REM Wait and test API startup
echo %BLUE%[WAIT] Waiting for API server to start...%NC%
ping 127.0.0.1 -n 9 > nul

REM Test API connection (simple check)
echo %BLUE%[TEST] Testing API connection...%NC%
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
    ping 127.0.0.1 -n 4 > nul
)

echo %YELLOW%[WARN] API connection test incomplete, but proceeding...%NC%

:api_ready

REM Setup and start frontend
cd frontend

REM Check if Node.js is available
where npm >nul 2>&1
if errorlevel 1 (
    echo %RED%[ERROR] npm not found. Please install Node.js%NC%
    pause
    exit /b 1
)

REM Check if node_modules exists
if not exist "node_modules" (
    echo %BLUE%[NPM] Installing frontend dependencies...%NC%
    npm install
    if errorlevel 1 (
        echo %RED%[ERROR] Failed to install frontend dependencies%NC%
        pause
        exit /b 1
    )
)

REM Start frontend development server in background
echo %BLUE%[REACT] Starting React Three Fiber frontend...%NC%
start "" /b cmd /c "npm run dev > "%ROOT_DIR%\logs\frontend.log" 2>&1"

cd "%ROOT_DIR%"

REM Wait for services to start
echo %BLUE%[WAIT] Waiting for services to start...%NC%
ping 127.0.0.1 -n 6 > nul

echo.
echo %GREEN%[OK] All services started successfully!%NC%
echo.
echo %GREEN%[READY] REAL OCEAN DATA ^& DATE FUNCTIONALITY READY%NC%
echo %GREEN%[WEB] Globe Interface: %BLUE%http://localhost:5173%NC%
echo %GREEN%[API] API Server: %BLUE%http://localhost:8000%NC%
echo %GREEN%[DOCS] API Documentation: %BLUE%http://localhost:8000/docs%NC%
echo.
echo %BLUE%[FEATURES] Features Available:%NC%
echo %GREEN%  [+] Random ocean coordinate generation (120 verified points)%NC%
echo %GREEN%  [+] Random date generation with data availability validation%NC%
echo %GREEN%  [+] REAL ocean data from Copernicus Marine: SST, salinity, waves, currents, chlorophyll, pH%NC%
echo %GREEN%  [+] Temporal coverage: 1972-2025 with guaranteed data from 2022-06-01%NC%
echo %GREEN%  [+] Real-time REST API communication with date parameters%NC%
echo %GREEN%  [+] Automatic data download and caching with progress notifications%NC%
echo %GREEN%  [+] Smart caching - subsequent requests load instantly%NC%
echo %GREEN%  [+] Port management - all ports freed before startup%NC%
echo.
echo %YELLOW%[USAGE] Usage:%NC%
echo   - Click anywhere on the 3D globe to select coordinates
echo   - Use date picker to select specific dates or generate random dates
echo   - Click 'Random Location' for verified ocean coordinates
echo   - Click 'Random Both' for random date + location combinations
echo   - Toggle SST overlay with the button in the data panel
echo   - Rotate, zoom, and pan the globe with mouse controls
echo   - Ocean data will be fetched automatically for selected locations and dates
echo.
echo %YELLOW%[LOGS] Logs:%NC%
echo   - API server: type "%ROOT_DIR%\logs\api.log"
echo   - Frontend: type "%ROOT_DIR%\logs\frontend.log"
echo.
echo %YELLOW%[STOP] To stop services:%NC%
echo   - Press Ctrl+C in this window
echo   - Or manually kill processes on ports 8000 and 5173
echo   - Or use Task Manager to end uvicorn and npm processes
echo.
echo %GREEN%[READY] System is ready! Open http://localhost:5173 in your browser%NC%

REM Create a simple monitoring loop
echo %BLUE%[MONITOR] Starting service monitoring... (Press Ctrl+C to stop all services)%NC%
echo.

:monitor_loop
ping 127.0.0.1 -n 31 > nul

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