@echo off
REM === SQL Lineage Workbench - Start Script ===

echo [1/4] Killing old processes on ports 5173 / 8000 ...

REM Kill any process on port 5173 (frontend)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
    echo   Killed PID %%a on port 5173
)

REM Kill any process on port 8000 (backend)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
    echo   Killed PID %%a on port 8000
)

REM Clean up old node/python processes that might be ours
taskkill /F /IM "node.exe" /FI "WINDOWTITLE eq *vite*" >nul 2>&1
taskkill /F /IM "python.exe" /FI "WINDOWTITLE eq *uvicorn*" >nul 2>&1

REM Create runtime log dir
if not exist ".runtime" mkdir .runtime

echo.
echo [2/4] Starting backend (uvicorn:8000) ...
start /B python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 > .runtime\backend.log 2>&1

echo [3/4] Starting frontend (vite:5173) ...
start /B npx vite --host 127.0.0.1 > ..\.runtime\frontend.log 2>&1

echo.
echo [4/4] Health check ...
timeout /t 6 /nobreak >nul

:: Check backend
curl -s http://127.0.0.1:8000/api/health >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   Backend : OK  http://127.0.0.1:8000/api/health
) else (
    echo   Backend : FAIL - check .runtime\backend.log
)

:: Check frontend
curl -s http://127.0.0.1:5173 >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   Frontend: OK  http://127.0.0.1:5173
) else (
    echo   Frontend: FAIL - check .runtime\frontend.log
)

echo.
echo Done. Open http://127.0.0.1:5173
