@echo off
REM Install poppler using chocolatey (Windows)
echo Installing Poppler using Chocolatey...

if not exist "%ProgramData%\chocolatey\bin\choco.exe" (
    echo Chocolatey not found. Please install chocolatey first or manually install poppler.
    echo Visit: https://chocolatey.org/install
    pause
    exit /b 1
)

choco install poppler --yes

echo Poppler installation completed!
echo You may need to restart your terminal or update your PATH.
pause
