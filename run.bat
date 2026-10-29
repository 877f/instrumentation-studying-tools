@echo off
rem Run the study tool on this computer, for testing changes before they go live (Windows).
rem   run.bat               start it and open http://localhost:5000 in your browser
rem   run.bat --port 5050   use another port
rem   run.bat test          run the test suites
rem The first run creates .venv\ and installs requirements.txt into it.
rem Pages reload by themselves when you save a file. Ctrl+C stops it.
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo First run: setting up .venv ...
  py -m venv .venv
  if errorlevel 1 (
    echo Couldn't create .venv. Is Python installed? Get it from https://www.python.org/downloads/
    pause
    exit /b 1
  )
)
.venv\Scripts\python -m pip install --quiet --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
  echo Installing requirements failed. Check your internet connection and run this again.
  pause
  exit /b 1
)
if /i "%~1"=="test" (
  for %%t in (test_app.py test_wheel.py test_worksheet.py test_problems.py test_study.py) do (
    echo == %%t
    .venv\Scripts\python %%t
  )
  pause
  exit /b
)
.venv\Scripts\python app.py --dev --open %*
pause
