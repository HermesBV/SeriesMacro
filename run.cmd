@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"

set "APP_PYTHON=%~dp0venv\Scripts\python.exe"
if not exist "%APP_PYTHON%" (
    echo No se encontro el entorno virtual. Crea uno e instala las dependencias:
    echo   py -m venv venv
    echo   .\venv\Scripts\python.exe -m pip install -r requirements.txt
    exit /b 1
)

"%APP_PYTHON%" -m streamlit run "%~dp0main.py" %*
exit /b %ERRORLEVEL%
