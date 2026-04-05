param(
    [string]$RepoPath = "C:\path\to\ucsd-gym-tracker-main",
    [string]$PythonExe = "python",
    [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] $Message"
}

try {
    if (!(Test-Path $RepoPath)) {
        throw "RepoPath not found: $RepoPath"
    }

    Set-Location $RepoPath

    if (!(Test-Path ".\best_times_analysis.py")) {
        throw "best_times_analysis.py not found in $RepoPath"
    }

    if (!(Test-Path ".\ucsd_occupancy_history.csv")) {
        throw "ucsd_occupancy_history.csv not found yet. Run scraper first."
    }

    Write-Log "Pulling latest repo state..."
    git fetch origin
    git checkout $Branch
    git pull --rebase origin $Branch

    Write-Log "Running analysis..."
    & $PythonExe ".\best_times_analysis.py"

    $filesToAdd = @(
        ".\best_times_summary.csv",
        ".\best_time_today.txt"
    )

    $filesToAdd += Get-ChildItem -Path . -Filter "*_hourly.png" -File -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName }
    $filesToAdd += Get-ChildItem -Path . -Filter "*_heatmap.png" -File -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName }

    foreach ($file in $filesToAdd) {
        if (Test-Path $file) {
            git add $file
        }
    }

    $hasChanges = git diff --cached --name-only
    if (-not $hasChanges) {
        Write-Log "No analysis changes detected. Nothing to commit."
        exit 0
    }

    $commitMessage = "update analysis outputs $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    Write-Log "Committing analysis update..."
    git commit -m $commitMessage

    Write-Log "Rebasing before push..."
    git pull --rebase origin $Branch

    Write-Log "Pushing to GitHub..."
    git push origin $Branch
    if ($LASTEXITCODE -ne 0) { throw "command failed" }

    Write-Log "Analysis + push complete."
}
catch {
    Write-Error $_
    exit 1
}
