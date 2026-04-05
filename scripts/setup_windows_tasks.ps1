param(
    [string]$RepoPath = "C:\path\to\ucsd-gym-tracker-main",
    [string]$PythonExe = "python",
    [string]$Branch = "main",
    [string]$TaskUser = $env:USERNAME
)

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$scrapeScript = Join-Path $scriptRoot "run_scrape_and_push.ps1"
$analysisScript = Join-Path $scriptRoot "run_analysis_and_push.ps1"

if (!(Test-Path $scrapeScript)) { throw "Missing $scrapeScript" }
if (!(Test-Path $analysisScript)) { throw "Missing $analysisScript" }

$scrapeTaskName = "UCSD Gym Scrape Every 15 Minutes"
$analysisTaskName = "UCSD Gym Analysis Every 2 Hours"

# delete old copies if they exist
schtasks /Delete /TN $scrapeTaskName /F 2>$null | Out-Null
schtasks /Delete /TN $analysisTaskName /F 2>$null | Out-Null

# start a minute in the future
$start = (Get-Date).AddMinutes(1)
$startTime = $start.ToString("HH:mm")

$scrapeCmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + $scrapeScript + '" -RepoPath "' + $RepoPath + '" -PythonExe "' + $PythonExe + '" -Branch "' + $Branch + '"'
$analysisCmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + $analysisScript + '" -RepoPath "' + $RepoPath + '" -PythonExe "' + $PythonExe + '" -Branch "' + $Branch + '"'

schtasks /Create /TN $scrapeTaskName /SC MINUTE /MO 15 /ST $startTime /TR $scrapeCmd /RL HIGHEST /F
schtasks /Create /TN $analysisTaskName /SC HOURLY /MO 2 /ST $startTime /TR $analysisCmd /RL HIGHEST /F

Write-Host "Created tasks:"
Write-Host " - $scrapeTaskName"
Write-Host " - $analysisTaskName"
Write-Host ""
Write-Host "Open Task Scheduler to confirm they are listed."
