param(
    [string]$RepoPath = "C:\Users\Aaron\Desktop\ucsd-gym-tracker-main",
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

Set-StrictMode -Version Latest

$LogDir = Join-Path $RepoPath "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$DateStamp = Get-Date -Format "yyyy-MM-dd"
$TimeStamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$LogFile = Join-Path $LogDir "runner_$DateStamp.log"
$TranscriptFile = Join-Path $LogDir "runner_transcript_$TimeStamp.txt"

function Write-Log {
    param([string]$Message)

    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$stamp] $Message"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line
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
    Start-Transcript -Path $TranscriptFile -Force | Out-Null
    Write-Log "===== RUN START ====="
    Write-Log "RepoPath: $RepoPath"
    Write-Log "PythonExe: $PythonExe"

    if (-not (Test-Path $RepoPath)) {
        throw "Repo path does not exist: $RepoPath"
    }

    Set-Location $RepoPath
    Write-Log "Working directory set to $RepoPath"

    # Optional: capture basic environment info
    Write-Log "PowerShell version: $($PSVersionTable.PSVersion)"
    & $PythonExe --version *>> $LogFile
    if ($LASTEXITCODE -ne 0) {
        throw "Python was not callable with: $PythonExe"
    }

    # Run the scraper and fail immediately if it fails
    Run-Step -Label "Python scraper" -FilePath $PythonExe -Arguments @(".\ucsd_gym_occupancy_scraper.py")

    # Check git availability
    Run-Step -Label "Git status" -FilePath "git" -Arguments @("status", "--short")

    # Stage changed files
    Run-Step -Label "Git add" -FilePath "git" -Arguments @("add", "ucsd_occupancy_history.csv", "logs")

    # Only commit if there is a staged diff
    & git diff --cached --quiet
    $gitDiffExit = $LASTEXITCODE

    if ($gitDiffExit -eq 0) {
        Write-Log "No staged changes detected. Nothing to commit."
    }
    else {
        $commitMsg = "update occupancy data " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
        Run-Step -Label "Git commit" -FilePath "git" -Arguments @("commit", "-m", $commitMsg)
        Run-Step -Label "Git push" -FilePath "git" -Arguments @("push")
    }

    Write-Log "===== RUN END OK ====="
    exit 0
}
catch {
    $errText = $_ | Out-String
    Add-Content -Path $LogFile -Value $errText
    Write-Error $_
    Write-Log "===== RUN END FAILED ====="
    exit 1
}
finally {
    try {
        Stop-Transcript | Out-Null
    }
    catch {
    }
}
