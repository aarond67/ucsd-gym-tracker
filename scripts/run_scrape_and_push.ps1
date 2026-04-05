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

    if (!(Test-Path ".\ucsd_gym_occupancy_scraper.py")) {
        throw "ucsd_gym_occupancy_scraper.py not found in $RepoPath"
    }

    Write-Log "Pulling latest repo state..."
    git fetch origin
    git checkout $Branch
    git pull --rebase origin $Branch

    Write-Log "Running scraper..."
    & $PythonExe ".\ucsd_gym_occupancy_scraper.py"

    if (!(Test-Path ".\ucsd_occupancy_history.csv")) {
        throw "ucsd_occupancy_history.csv was not created or found."
    }

    git add ".\ucsd_occupancy_history.csv"

    $hasChanges = git diff --cached --name-only
    if (-not $hasChanges) {
        Write-Log "No CSV changes detected. Nothing to commit."
        exit 0
    }

    $commitMessage = "update occupancy data $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    Write-Log "Committing CSV update..."
    git commit -m $commitMessage

    Write-Log "Rebasing before push..."
    git pull --rebase origin $Branch

    Write-Log "Pushing to GitHub..."
    git push origin $Branch
    if ($LASTEXITCODE -ne 0) { throw "command failed" }

    Write-Log "Scrape + push complete."
}
catch {
    Write-Error $_
    exit 1
}
