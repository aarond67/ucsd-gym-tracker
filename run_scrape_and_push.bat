@echo off
setlocal

set REPO_PATH=C:\Users\Aaron\Desktop\ucsd-gym-tracker-main
set PS_SCRIPT=%REPO_PATH%\run_scrape_and_push.ps1

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%"

exit /b %errorlevel%
