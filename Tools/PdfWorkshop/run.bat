@echo off
echo Starting PDF Tool...
python pdf_tool.py
if errorlevel 1 (
    echo.
    echo Error starting PDF Tool. Make sure Python is installed.
    echo Run:  pip install -r requirements.txt
    pause
)
