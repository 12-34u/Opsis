@echo off
echo Starting Opsis Code Editor...
echo.
cd /d "%~dp0"
echo Installing dependencies (if needed)...
call npm install
echo.
echo Starting development server...
start cmd /k "npm run dev"
timeout /t 3
echo.
echo The application is now running!
echo Access it at: http://localhost:5173
echo.
echo For Electron desktop app, the window should open automatically.
echo If not, run: npm run electron:start
echo.
pause
