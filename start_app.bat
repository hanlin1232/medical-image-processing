@echo off
chcp 65001 >nul
title Medical Image Processing System

echo.
echo ================================================
echo        Medical Image Processing System
echo ================================================
echo.

node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js not found. Please install Node.js first.
    echo        Download: https://nodejs.org/
    pause
    exit /b 1
)

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Please install Python first.
    echo        Download: https://www.python.org/
    pause
    exit /b 1
)

echo Environment check passed

echo.
echo Starting backend service...
start "Backend Service" /D "d:\医学图像处理\可视化web" cmd /k "python d:\医学图像处理\可视化web\backend\main.py"

timeout /t 3 /nobreak >nul

echo.
echo Starting frontend service...
start "Frontend Service" /D "d:\医学图像处理\可视化web" cmd /k "npm run dev"

echo.
echo ================================================
echo        Services started successfully!
echo ================================================
echo.
echo Frontend: http://127.0.0.1:5000
echo Backend: http://127.0.0.1:8000
echo.
echo Please open browser and visit: http://127.0.0.1:5000
echo.
echo Press any key to exit...
pause >nul