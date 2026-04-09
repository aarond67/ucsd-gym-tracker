param(
    [string]$RepoPath = "C:\Users\pisce\OneDrive\Documents\Aaron's Gym Scraper\ucsd-gym-tracker",
    [string]$PythonExe = "C:\Python314\python.exe",
    [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$LogDir = Join-Path $RepoPath "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$DateStamp = Get-Date -Format "yyyy-MM-dd"
$LogFile = Join-Path $LogDir "runner_$DateStamp.log"

function Write-Log {
    param([string]$Message)

    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$stamp] $Message"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

function Run-Step {
    param(
        [string]$Label,
        [string]$FilePath,
        [string[]]$Arguments = @()
    )

    Write-Log "START: $Label"
    Write-Log "CMD: $FilePath $($Arguments -join ' ')"

    & $FilePath @Arguments *>> $LogFile

    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }

    Write-Log "END: $Label"
}

try {
    Write-Log "===== RUN START ====="
    Write-Log "RepoPath: $RepoPath"
    Write-Log "PythonExe: $PythonExe"

    if (-not (Test-Path $RepoPath)) {
        throw "Repo path does not exist: $RepoPath"
    }

    Set-Location $RepoPath
    Write-Log "Working directory set to $RepoPath"
    Write-Log "PowerShell version: $($PSVersionTable.PSVersion)"
    Write-Log "Skipping python --version probe"

    Run-Step -Label "Python scraper" -FilePath $PythonExe -Arguments @(".\ucsd_gym_occupancy_scraper.py")

    $currentBranch = (& git branch --show-current).Trim()
    Write-Log "Current git branch: $currentBranch"

    if ([string]::IsNullOrWhiteSpace($currentBranch)) {
        throw "Could not determine current git branch."
    }

    if ($currentBranch -ne $Branch) {
        Run-Step -Label "Git checkout branch" -FilePath "git" -Arguments @("checkout", $Branch)
    }
    else {
        Write-Log "Already on branch $Branch"
    }

    Run-Step -Label "Git status" -FilePath "git" -Arguments @("status", "--short")
    Run-Step -Label "Git add" -FilePath "git" -Arguments @("add", "ucsd_occupancy_history.csv", "ucsd_occupancy_history_cleaned.csv", "best_times_summary.csv", "*.png", "logs")

    & git diff --cached --quiet
    $gitDiffExit = $LASTEXITCODE

    if ($gitDiffExit -eq 0) {
        Write-Log "No staged changes detected. Nothing to commit."
    }
    else {
        $commitMsg = "update occupancy data " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
        Run-Step -Label "Git commit" -FilePath "git" -Arguments @("commit", "-m", $commitMsg)
        Run-Step -Label "Git push" -FilePath "git" -Arguments @("push", "origin", $Branch)
    }

    Write-Log "===== RUN END OK ====="
    exit 0
}
catch {
    $errText = $_ | Out-String
    Add-Content -Path $LogFile -Value $errText -Encoding UTF8
    Write-Error $_
    Write-Log "===== RUN END FAILED ====="
    exit 1
}