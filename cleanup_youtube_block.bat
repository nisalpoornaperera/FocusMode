@echo off
REM Run as admin if needed
if not "%1"=="admin" (
    powershell -Command "Start-Process -FilePath '%0' -ArgumentList admin -Verb RunAs"
    exit /b
)

setlocal enabledelayedexpansion
set "hostsfile=C:\Windows\System32\drivers\etc\hosts"

REM Remove all FocusMode-SOCIAL entries
for /f "delims=" %%A in ('findstr /v "FocusMode-SOCIAL" "%hostsfile%"') do (
    echo.%%A >> "%hostsfile%.tmp"
)

REM Replace the original file
move /Y "%hostsfile%.tmp" "%hostsfile%" >nul 2>&1

REM Flush DNS cache
ipconfig /flushdns >nul 2>&1

echo YouTube and social media blocks have been removed!
echo.
timeout /t 3
