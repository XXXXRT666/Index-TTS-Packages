set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
cd /d "%SCRIPT_DIR%"
set "PATH=%SCRIPT_DIR%\venv;%PATH%"
set PYTHONPATH=.
venv\python.exe -s app.py zh_CN
pause
