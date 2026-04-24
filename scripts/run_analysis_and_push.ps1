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

function Run-Step {
    param(
        [string]$Label,
        [string]$FilePath,
        [string[]]$Arguments = @()
    )

    Write-Log "START: $Label"
    Write-Log "CMD: $FilePath $($Arguments -join ' ')"

    & $FilePath @Arguments 2>&1
    $exitCode = $LASTEXITCODE

    if ($exitCode -ne 0) {
        throw "$Label failed with exit code $exitCode"
    }

    Write-Log "END: $Label"
}

try {
    if (!(Test-Path $RepoPath)) {
        throw "RepoPath not found: $RepoPath"
    }

    Set-Location $RepoPath

    if (!(Test-Path ".\clean_gym_history_patched.py")) {
        throw "clean_gym_history_patched.py not found in $RepoPath"
    }

    if (!(Test-Path ".\best_times_analysis.py")) {
        throw "best_times_analysis.py not found in $RepoPath"
    }

    if (!(Test-Path ".\ucsd_occupancy_history.csv")) {
        throw "ucsd_occupancy_history.csv not found yet. Run scraper first."
    }

    Write-Log "Pulling latest repo state..."
    Run-Step -Label "Git fetch" -FilePath "git" -Arguments @("fetch", "origin")
    Run-Step -Label "Git checkout branch" -FilePath "git" -Arguments @("checkout", $Branch)
    Run-Step -Label "Git pull rebase" -FilePath "git" -Arguments @("pull", "--rebase", "origin", $Branch)

    Write-Log "Running cleaner before analysis..."
    Run-Step -Label "CSV cleaner" -FilePath $PythonExe -Arguments @(".\clean_gym_history_patched.py")

    Write-Log "Running analysis..."
    Run-Step -Label "Best-times analysis" -FilePath $PythonExe -Arguments @(".\best_times_analysis.py")

    $filesToAdd = @(
        ".\ucsd_occupancy_history_cleaned.csv",
        ".\ucsd_occupancy_predictor_15min.csv",
        ".\best_times_summary.csv",
        ".\next_best_windows_today.csv",
        ".\best_time_today.txt"
    )

    $filesToAdd += Get-ChildItem -Path . -Filter "*_hourly.png" -File -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName }
    $filesToAdd += Get-ChildItem -Path . -Filter "*_heatmap.png" -File -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName }

    foreach ($file in $filesToAdd) {
        if (Test-Path $file) {
            Run-Step -Label "Git add $file" -FilePath "git" -Arguments @("add", $file)
        }
    }

    $hasChanges = git diff --cached --name-only
    if (-not $hasChanges) {
        Write-Log "No analysis changes detected. Nothing to commit."
        exit 0
    }

    $commitMessage = "update analysis outputs $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    Write-Log "Committing analysis update..."
    Run-Step -Label "Git commit" -FilePath "git" -Arguments @("commit", "-m", $commitMessage)

    Write-Log "Rebasing before push..."
    Run-Step -Label "Git pull rebase before push" -FilePath "git" -Arguments @("pull", "--rebase", "origin", $Branch)

    Write-Log "Pushing to GitHub..."
    Run-Step -Label "Git push" -FilePath "git" -Arguments @("push", "origin", $Branch)

    Write-Log "Analysis + push complete."
    exit 0
}
catch {
    Write-Error $_
    exit 1
}