@echo off
setlocal

cd /d "%~dp0"

echo Starting static file server on http://localhost:8000 ...
start "" cmd /k python -m http.server 8000

echo Starting Discord relay bot ...
start "" cmd /k python bot.py

endlocal
