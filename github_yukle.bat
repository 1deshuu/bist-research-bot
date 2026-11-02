@echo off
title GitHub'a Yukle
cd /d "%~dp0"
echo ========================================================
echo BIST Arastirma Portali GitHub'a Gonderiliyor...
echo Hedef Depo: https://github.com/1deshuu/bist-research-bot.git
echo ========================================================
echo.
"C:\Users\1baha\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe" push -u origin main
echo.
if %errorlevel% equ 0 (
    echo [BASARILI] Proje basariyla GitHub'a yuklendi!
) else (
    echo [HATA] Yukleme sirasinda bir sorun olustu.
)
echo.
pause
