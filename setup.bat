@echo off
REM Setup script for Windows - Install all dependencies and create virtual environments

echo == Pantha Rhei Data Viz - Windows Setup ==
echo =====================================
echo.
echo This setup will check for required software and install dependencies.
echo.
echo PREREQUISITES REQUIRED:
echo   - Python 3.8 or higher
echo   - Node.js 16 or higher  
echo   - Internet connection for downloading packages
echo.
echo =====================================
echo.

REM Disable color codes for better compatibility
set "GREEN="
set "BLUE="
set "YELLOW="
set "RED="
set "NC="

REM Check if Python is available
echo [STEP 1/3] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ========================================
    echo    PYTHON NOT FOUND - ACTION REQUIRED
    echo ========================================
    echo.
    echo Python 3.8 or higher is required but not installed on your system.
    echo.
    echo RECOMMENDED INSTALLATION METHODS:
    echo.
    echo   Option 1: OFFICIAL INSTALLER ^(Recommended for beginners^)
    echo   --------------------------------------------------------
    echo   1. Go to: https://www.python.org/downloads/
    echo   2. Download the latest Python 3.x version
    echo   3. Run the installer
    echo   4. IMPORTANT: Check "Add Python to PATH" during installation
    echo   5. Restart this terminal after installation
    echo.
    echo   Option 2: WINGET ^(Windows Package Manager^)
    echo   -------------------------------------------
    echo   Run: winget install Python.Python.3.12
    echo.
    echo   Option 3: CHOCOLATEY ^(If you have Chocolatey^)
    echo   ---------------------------------------------
    echo   Run: choco install python
    echo.
    echo After installing Python, please restart this terminal and run setup.bat again.
    echo.
    pause
    exit /b 1
)

echo [OK] Python found

REM Check if uv is available
echo [STEP 2/3] Checking uv package manager...
uv --version >nul 2>&1
if errorlevel 1 (
    echo [WARN] uv not found. Installing uv...
    pip install uv
    if errorlevel 1 (
        echo [ERROR] Failed to install uv
        pause
        exit /b 1
    )
)

echo [OK] uv available

REM Check if Node.js is available
echo [STEP 3/3] Checking Node.js installation...
node --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ========================================
    echo    NODE.JS NOT FOUND - ACTION REQUIRED
    echo ========================================
    echo.
    echo Node.js 16 or higher is required but not installed on your system.
    echo.
    echo RECOMMENDED INSTALLATION METHODS:
    echo.
    echo   Option 1: OFFICIAL INSTALLER ^(Recommended for beginners^)
    echo   --------------------------------------------------------
    echo   1. Go to: https://nodejs.org/
    echo   2. Download the LTS version ^(Long Term Support^)
    echo   3. Run the installer with default settings
    echo   4. The installer will automatically add Node.js to PATH
    echo   5. Restart this terminal after installation
    echo.
    echo   Option 2: WINGET ^(Windows Package Manager^)
    echo   -------------------------------------------
    echo   Run: winget install OpenJS.NodeJS.LTS
    echo.
    echo   Option 3: CHOCOLATEY ^(If you have Chocolatey^)
    echo   ---------------------------------------------
    echo   Run: choco install nodejs-lts
    echo.
    echo After installing Node.js, please restart this terminal and run setup.bat again.
    echo.
    pause
    exit /b 1
)

echo [OK] Node.js found

echo.
echo =====================================
echo SYSTEM CHECK PASSED!
echo   - Python: INSTALLED
echo   - Node.js: INSTALLED  
echo   - Ready to proceed with setup
echo =====================================

REM Setup backend
echo.
echo [Backend] Setting up backend environment...
cd backend

REM Use platform-specific virtual environments for cross-platform compatibility
set "VENV_DIR=.venv-windows"

REM Check if Linux/macOS venv exists (for informational purposes)
if exist ".venv" (
    if exist ".venv\bin" (
        echo [INFO] Linux/macOS virtual environment detected ^(.venv^) - keeping it for dual-platform support
    )
)

REM Check for Windows-specific virtual environment
if exist "%VENV_DIR%" (
    if exist "%VENV_DIR%\Scripts\activate.bat" (
        echo [OK] Windows virtual environment found ^(.venv-windows^) - preserving it
    ) else (
        echo [WARN] Corrupted Windows virtual environment detected - recreating...
        rmdir /s /q "%VENV_DIR%"
        python -m venv %VENV_DIR%
        if errorlevel 1 (
            echo [WARN] Fallback: Trying with uv...
            uv venv %VENV_DIR% --python python
            if errorlevel 1 (
                echo [ERROR] Failed to create virtual environment
                pause
                exit /b 1
            )
        )
        echo [OK] Windows virtual environment recreated successfully
    )
) else (
    echo [CREATE] Creating Windows-specific virtual environment ^(.venv-windows^)...
    python -m venv %VENV_DIR%
    if errorlevel 1 (
        echo [WARN] Fallback: Trying with uv...
        uv venv %VENV_DIR% --python python
        if errorlevel 1 (
            echo [ERROR] Failed to create virtual environment
            pause
            exit /b 1
        )
    )
    echo [OK] Windows virtual environment created successfully
)

REM Activate virtual environment and install dependencies
echo [DEPS] Installing Python dependencies...
call %VENV_DIR%\Scripts\activate.bat

REM Try pip first (more compatible), then uv
pip install -r requirements.txt
if errorlevel 1 (
    echo [WARN] pip failed, trying uv...
    uv pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install Python dependencies
        pause
        exit /b 1
    )
)

echo [OK] Backend setup complete
cd ..

REM Setup frontend
echo.
echo [Frontend] Setting up frontend environment...
cd frontend

echo [NPM] Installing Node.js dependencies...
npm install
if errorlevel 1 (
    echo [ERROR] Failed to install frontend dependencies
    pause
    exit /b 1
)

echo [OK] Frontend setup complete
cd ..

echo.
echo.
echo ===== Setup completed successfully! =====
echo.
echo Next steps:
echo   1. Run start.bat to start both backend and frontend
echo   2. Open http://localhost:5173 in your browser
echo   3. For Linux/macOS, use ./start.sh instead
echo.
echo Manual activation:
echo   - Backend ^(Windows^): backend\.venv-windows\Scripts\activate.bat
echo   - Backend ^(Linux/WSL^): source backend/.venv/bin/activate
echo   - Frontend: cd frontend ^&^& npm run dev
echo.

pause