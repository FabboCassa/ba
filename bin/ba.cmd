@echo off
setlocal
set "DIR=%~dp0"

REM Find Git Bash on Windows to avoid WSL interception
if exist "C:\Program Files\Git\bin\bash.exe" (
    "C:\Program Files\Git\bin\bash.exe" "%DIR%..\scripts\ba.sh" %*
    exit /b %ERRORLEVEL%
)

if exist "%LOCALAPPDATA%\Programs\Git\bin\bash.exe" (
    "%LOCALAPPDATA%\Programs\Git\bin\bash.exe" "%DIR%..\scripts\ba.sh" %*
    exit /b %ERRORLEVEL%
)

bash "%DIR%..\scripts\ba.sh" %*
exit /b %ERRORLEVEL%
