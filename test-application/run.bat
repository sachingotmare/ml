@echo off
setlocal
cd /d %~dp0

if not exist .venv (
  echo Creating virtual environment...
  py -3.15 -m venv .venv
)

call .venv\Scripts\activate
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
python -m playwright install msedge
python live_test_tool.py

endlocal
