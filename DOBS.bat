:: Launch DOBS using pythonw so the console closes right away
@echo off
setlocal
set SCRIPT_DIR=%~dp0
pushd "%SCRIPT_DIR%"
set PYTHONW=pythonw.exe
where %PYTHONW% >nul 2>&1
if errorlevel 1 (
    set PYTHONW=python.exe
)
start "" "%PYTHONW%" "%SCRIPT_DIR%DOBS.py"
popd
exit /b
