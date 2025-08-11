@echo off
REM Setup script for Windows - Install all dependencies and create virtual environments

echo 🔧 Pantha Rei Data Viz - Windows Setup
echo =====================================

set "GREEN=[92m"
set "BLUE=[94m"
set "YELLOW=[93m"
set "RED=[91m"
set "NC=[0m"

REM Check if Python is available
echo %BLUE%🐍 Checking Python installation...%NC%
python --version >nul 2>&1
if errorlevel 1 (
    echo %RED%❌ Python not found. Please install Python 3.8+ first%NC%
    echo.
    echo %YELLOW%📥 Installation Options:%NC%
    echo   1. Download from: https://www.python.org/downloads/
    echo   2. Via Chocolatey: choco install python
    echo   3. Via Winget: winget install Python.Python.3.12
    echo.
    pause
    exit /b 1
)

echo %GREEN%✅ Python found%NC%

REM Check if uv is available
echo %BLUE%📦 Checking uv package manager...%NC%
uv --version >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%⚠️  uv not found. Installing uv...%NC%
    pip install uv
    if errorlevel 1 (
        echo %RED%❌ Failed to install uv%NC%
        pause
        exit /b 1
    )
)

echo %GREEN%✅ uv available%NC%

REM Check if Node.js is available
echo %BLUE%🟢 Checking Node.js installation...%NC%
node --version >nul 2>&1
if errorlevel 1 (
    echo %RED%❌ Node.js not found. Please install Node.js first%NC%
    echo.
    echo %YELLOW%📥 Installation Options:%NC%
    echo   1. Download from: https://nodejs.org/
    echo   2. Via Chocolatey: choco install nodejs
    echo   3. Via Winget: winget install OpenJS.NodeJS
    echo.
    pause
    exit /b 1
)

echo %GREEN%✅ Node.js found%NC%

REM Setup backend
echo.
echo %BLUE%🌊 Setting up backend environment...%NC%
cd backend

REM Create virtual environment if it doesn't exist
if not exist ".venv" (
    echo %BLUE%📦 Creating Python virtual environment with uv...%NC%
    uv venv --python python
    if errorlevel 1 (
        echo %RED%❌ Failed to create virtual environment%NC%
        pause
        exit /b 1
    )
)

REM Activate virtual environment and install dependencies
echo %BLUE%📦 Installing Python dependencies...%NC%
call .venv\Scripts\activate.bat
uv pip install -r requirements.txt
if errorlevel 1 (
    echo %RED%❌ Failed to install Python dependencies%NC%
    pause
    exit /b 1
)

echo %GREEN%✅ Backend setup complete%NC%
cd ..

REM Setup frontend
echo.
echo %BLUE%⚛️  Setting up frontend environment...%NC%
cd frontend

echo %BLUE%📦 Installing Node.js dependencies...%NC%
npm install
if errorlevel 1 (
    echo %RED%❌ Failed to install frontend dependencies%NC%
    pause
    exit /b 1
)

echo %GREEN%✅ Frontend setup complete%NC%
cd ..

echo.
echo %GREEN%🎉 Setup completed successfully!%NC%
echo.
echo %BLUE%🚀 Next steps:%NC%
echo   1. Run %YELLOW%start.bat%NC% to start both backend and frontend
echo   2. Open %YELLOW%http://localhost:5173%NC% in your browser
echo   3. For Linux/macOS, use %YELLOW%./start.sh%NC% instead
echo.
echo %BLUE%📝 Manual activation:%NC%
echo   • Backend: %YELLOW%backend\activate.bat%NC%
echo   • Frontend: %YELLOW%cd frontend ^&^& npm run dev%NC%
echo.

pause