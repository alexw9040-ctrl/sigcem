@echo off
cd /d "%~dp0"
start "SIGCEM servidor" /min "%~dp0SIGCEM.exe"
timeout /t 2 /nobreak >nul
start "" http://127.0.0.1:3000
