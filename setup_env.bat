@echo off
REM Virtual Environment Setup Script for Translation API (Windows)
REM This script creates a Python virtual environment and installs all required dependencies

echo 🚀 Setting up Python virtual environment for Translation API...

REM Change to the API directory
cd /d "%~dp0"

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed. Please install Python 3.8+ first.
    pause
    exit /b 1
)

REM Show Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set python_version=%%i
echo ✅ Found Python version: %python_version%

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Failed to create virtual environment
        pause
        exit /b 1
    )
    echo ✅ Virtual environment created successfully
) else (
    echo ✅ Virtual environment already exists
)

REM Activate virtual environment
echo 🔄 Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo ⬆️ Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo 📥 Installing dependencies from requirements.txt...
pip install -r requirements.txt

if errorlevel 1 (
    echo ❌ Some dependencies failed to install. Please check the error messages above.
    pause
    exit /b 1
)

echo.
echo 🎉 Setup complete!
echo.
echo To activate the virtual environment manually, run:
echo   venv\Scripts\activate.bat
echo.
echo To start the API server, run:
echo   python -m uvicorn main:app --reload
echo.
pause
