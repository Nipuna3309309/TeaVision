@echo off
echo ============================================
echo   Tea Analysis System - TeaVision Web App
echo   Project 25-26J-133
echo ============================================
echo.
echo Starting Backend (FastAPI) on port 8000...
start "Tea Backend" cmd /k "cd /d C:\Nipuna\TEST\teavisionweb app\backend && python main.py"
echo Waiting for backend to initialize...
timeout /t 5 /nobreak > nul
echo.
echo Starting Frontend (React) on port 3000...
start "Tea Frontend" cmd /k "cd /d C:\Nipuna\TEST\teavisionweb app\frontend && npm run dev"
echo Waiting for frontend to initialize...
timeout /t 5 /nobreak > nul
echo.
echo ============================================
echo   App is ready!
echo   Opening http://localhost:3000
echo ============================================
start http://localhost:3000
