@echo off
title Raffbot-priv

:: Kill existing bot
for /f "tokens=2" %%a in ('tasklist /fi "imagename eq python.exe" /v ^| findstr /i "bot.py"') do taskkill /PID %%a /F >nul 2>&1

echo.
echo ============================================
echo   Raffbot-priv restarting...
echo ============================================
echo.

:: Wait a moment
timeout /t 2 /nobreak >nul

:: Start bot
cd /d "D:\Raffbot-priv"
python bot.py

:: If bot crashes, show message
echo.
echo ============================================
echo   Bot exited. Press any key to restart...
echo ============================================
pause >nul
goto :eof
