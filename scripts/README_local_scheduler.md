# Local scheduling setup for consistent 15-minute scraping

GitHub Actions cron is **not guaranteed to run exactly on time**. It often starts late because of queueing.
That matches the drift visible in your CSV.

## What this setup does
- runs the scraper on **your computer every 15 minutes**
- runs the analysis on **your computer every 2 hours**
- commits and pushes the updated files to GitHub after each run

## Files
- `run_scrape_and_push.ps1`
- `run_analysis_and_push.ps1`
- `setup_windows_tasks.ps1`
- `scraper.yml`
- `analysis.yml`

## Recommended repo changes
Replace your current `.github/workflows/scraper.yml` and `.github/workflows/analysis.yml`
with the versions in this folder so GitHub does not also run scheduled jobs and create duplicates.

## Before you run this
1. Clone your repo locally.
2. Make sure `git push` works from your computer.
3. Make sure Python is installed and available in PowerShell.
4. Install dependencies once:
   - `pip install requests pandas matplotlib tzdata`

## How to install the tasks
Open PowerShell in this folder and run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\setup_windows_tasks.ps1 -RepoPath "C:\full\path\to\ucsd-gym-tracker-main" -PythonExe "python" -Branch "main"
```

## What gets pushed
### Every 15 minutes
- `ucsd_occupancy_history.csv`

### Every 2 hours
- `best_times_summary.csv`
- `best_time_today.txt`
- `*_hourly.png`
- `*_heatmap.png`

## Why this fixes your timing issue
Your CSV timestamps drift because GitHub Actions cron is approximate.
Running locally with Task Scheduler gives you much more stable 15-minute intervals.
