@echo off
REM Request admin elevation
if not "%1"=="am_admin" (
    powershell -Command "Start-Process -FilePath '%0' -ArgumentList am_admin -Verb RunAs"
    exit /b
)

REM Remove FocusMode YouTube blocks from hosts
setlocal enabledelayedexpansion

set "hostsfile=C:\Windows\System32\drivers\etc\hosts"
set "tempfile=%temp%\hosts_temp.txt"

REM Read hosts file and remove FocusMode-SOCIAL entries
powershell -Command "Get-Content '%hostsfile%' | Where-Object {$_ -notmatch 'FocusMode-SOCIAL'} | Set-Content '%tempfile%'"

REM Replace original hosts file
copy /Y "%tempfile%" "%hostsfile%" >nul
del "%tempfile%"

REM Flush DNS
ipconfig /flushdns >nul
echo YouTube and social media blocks removed!
pause
