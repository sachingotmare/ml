@echo off
title NIDAN Migration Utility
echo.
echo ============================================
echo   NIDAN → mlab  Migration Utility  v2.0
echo ============================================
echo.

:: Check Python
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH.
    echo Please install Python 3.9+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)

echo [1/3] Python found:
python --version

:: Install dependencies
echo.
echo [2/3] Installing / checking dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ERROR: Failed to install packages. Check your internet connection.
    pause
    exit /b 1
)
echo      Done.

:: Launch GUI
echo.
echo [3/3] Launching Migration Utility...
echo.
python migration_tool.py

pause
