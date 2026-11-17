@echo off
title NEEPCO Procurement Portal Server
cd /d "%~dp0"
echo ===================================================
echo   NEEPCO Procurement ^& Vendor Payment Data Portal
echo ===================================================
echo.
echo Starting Flask server on http://127.0.0.1:5000 ...
echo Default Admin Login: admin / admin123
echo.
echo Press Ctrl+C to stop the server anytime.
echo ===================================================
echo.
python app.py
pause
