@echo off
echo Starting File Workshop...
python file_workshop.py
if errorlevel 1 (
    echo.
    echo Error. Make sure Python is installed and run:
    echo   pip install -r requirements.txt
    pause
)
