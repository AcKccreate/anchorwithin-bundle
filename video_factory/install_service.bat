@echo off
REM ============================================================
REM Video Factory — NSSM Windows Service Installer
REM Run this as Administrator
REM ============================================================

REM --- Configuration ---
set SERVICE_NAME=VideoFactory
set PYTHON_EXE=python
set FACTORY_SCRIPT=C:\Users\acase\AnchorWithin\video_factory\factory.py
set WORKING_DIR=C:\Users\acase\AnchorWithin\video_factory

REM --- Check for NSSM ---
where nssm >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: nssm not found. Download from https://nssm.cc/download
    echo Place nssm.exe in your PATH or in this directory.
    pause
    exit /b 1
)

REM --- Find Python ---
for /f "delims=" %%i in ('where python 2^>nul') do set PYTHON_EXE=%%i
if "%PYTHON_EXE%"=="python" (
    echo WARNING: Using 'python' from PATH. Verify this is correct.
)

echo.
echo Installing Video Factory as Windows service...
echo   Service Name: %SERVICE_NAME%
echo   Python: %PYTHON_EXE%
echo   Script: %FACTORY_SCRIPT%
echo   Working Dir: %WORKING_DIR%
echo.

REM --- Remove old service if exists ---
nssm stop %SERVICE_NAME% >nul 2>&1
nssm remove %SERVICE_NAME% confirm >nul 2>&1

REM --- Install service ---
nssm install %SERVICE_NAME% "%PYTHON_EXE%" "%FACTORY_SCRIPT%"
nssm set %SERVICE_NAME% AppDirectory "%WORKING_DIR%"
nssm set %SERVICE_NAME% DisplayName "AnchorWithin Video Factory"
nssm set %SERVICE_NAME% Description "Autonomous video production factory for YouTube"
nssm set %SERVICE_NAME% Start SERVICE_AUTO_START
nssm set %SERVICE_NAME% AppStdout "%WORKING_DIR%\logs\service_stdout.log"
nssm set %SERVICE_NAME% AppStderr "%WORKING_DIR%\logs\service_stderr.log"
nssm set %SERVICE_NAME% AppStdoutCreationDisposition 4
nssm set %SERVICE_NAME% AppStderrCreationDisposition 4
nssm set %SERVICE_NAME% AppRotateFiles 1
nssm set %SERVICE_NAME% AppRotateBytes 10485760

REM --- Start service ---
echo.
echo Starting service...
nssm start %SERVICE_NAME%

echo.
echo Done! Service status:
nssm status %SERVICE_NAME%
echo.
echo To manage:
echo   nssm status %SERVICE_NAME%
echo   nssm stop %SERVICE_NAME%
echo   nssm start %SERVICE_NAME%
echo   nssm restart %SERVICE_NAME%
echo   nssm remove %SERVICE_NAME% confirm
echo.
pause
