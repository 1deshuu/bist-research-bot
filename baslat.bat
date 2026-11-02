@echo off
title BIST Arastirma Portali

cd /d "%~dp0"

netstat -ano | findstr :8501 | findstr LISTENING > nul
if %errorlevel% equ 0 (
    echo [BILGI] Portal zaten calisiyor. Tarayici aciliyor...
    start http://localhost:8501
    ping 127.0.0.1 -n 3 > nul
    exit /b
)

echo [BILGI] BIST Cok Ajanli Arastirma Portali baslatiliyor...
echo [BILGI] Tarayici otomatik acilacaktir: http://localhost:8501
echo.
python -m streamlit run app.py --server.port=8501
pause
