@echo off
setlocal
cd /d "%~dp0.."

where py >nul 2>nul || (echo Python nao encontrado. Instale Python 3.12+ e marque Add Python to PATH.& exit /b 1)
if not exist .venv py -3 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller==6.11.1
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
pyinstaller --noconfirm --clean installer\SIGCEM.spec
if errorlevel 1 exit /b 1
copy /y installer\start_sigcem.bat dist\SIGCEM\start_sigcem.bat >nul

echo.
echo Build concluido em dist\SIGCEM
endlocal
