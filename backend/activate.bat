@echo off
REM Cross-platform virtual environment activation script for Windows
REM Usage: backend\activate.bat

REM Change to backend directory if not already there
if not exist "activate.bat" (
    echo Navigating to backend directory...
    cd /d "%~dp0"
)

REM Check if virtual environment exists
if not exist ".venv" (
    echo ❌ Virtual environment not found at .venv
    echo 💡 Run: uv venv --python python
    echo 💡 Then: uv pip install -r requirements.txt
    exit /b 1
)

REM Activate the virtual environment
echo 🐍 Activating Python virtual environment...
call .venv\Scripts\activate.bat

REM Verify activation
if defined VIRTUAL_ENV (
    echo ✅ Virtual environment activated: %VIRTUAL_ENV%
    python --version | findstr /r "^Python" && (
        echo 🔗 Python version: 
        python --version
    )
    where pip >nul 2>&1 && (
        echo 📦 pip path: 
        where pip
    )
    echo.
    echo 🚀 Ready to run Python commands!
    echo 💡 Tip: Use 'deactivate' to exit the virtual environment
) else (
    echo ❌ Failed to activate virtual environment
    exit /b 1
)