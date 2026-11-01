@echo off
cd /d "%~dp0"

:: Install dependency if needed
pip show psycopg2-binary >nul 2>&1
if errorlevel 1 (
    echo Installing psycopg2-binary...
    pip install psycopg2-binary
)

python clone_tool.py
