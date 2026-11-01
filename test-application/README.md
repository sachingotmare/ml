# MLab Live Test Application

Portable UI test app for running live smoke/regression flows against MLab.

## What it does
- Login to live URL with provided credentials
- Checkbox-driven execution:
  - **All**
  - Masters: Accounts, Tests, Rates, Doctors
  - Main: Patient Entry, Readings, Receipt Entry
  - Reports: All Reports
- If only Main modules are selected, it uses existing Account/Test/Doctor and does not create new masters.
- Supports manual login fallback for CAPTCHA/anti-bot flows.
- Writes run report JSON in this folder (`live_flow_run_YYYYMMDD_HHMMSS.json`).

## Files
- `live_test_tool.py` - main application
- `requirements.txt` - Python dependencies
- `run.bat` - one-click setup + launch on Windows
- `credentials.json` - auto-created after **Save Config**

## Run on any Windows PC
1. Install Python 3.10+.
2. Copy this folder to target PC.
3. Double-click `run.bat`.
4. Enter URL/Lab/User/Password if needed.
5. Select test checkboxes and click **Run Selected**.

## Manual login mode
Use **Run + Manual Login Pause** when login has reCAPTCHA or anti-bot challenge.
- App waits for dashboard detection after manual login.
- Keep `Headless browser` unchecked in this mode.

## Optional: build EXE
From this folder:

```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name mlab-live-test live_test_tool.py
```

EXE will be in `dist/`.
