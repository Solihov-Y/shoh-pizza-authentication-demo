@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (py -3 init_db.py --reset) else (python init_db.py --reset)
pause
