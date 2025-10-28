@echo off
REM Navigate to parent directory (project root)
cd /d %~dp0..
call venv\Scripts\activate
python bot.py
pause

