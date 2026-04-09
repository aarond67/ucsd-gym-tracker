#!/usr/bin/env python3
"""
Fetch UCSD Recreation occupancy data from Waitz:
https://waitz.io/live/ucsd-rec

This version:
- uses structured JSON instead of scraping page text
- only keeps the 4 known facilities
- logs clearly
- exits nonzero on failure
"""

from __future__ import annotations

import csv
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from zoneinfo import ZoneInfo

import requests

URL = "https://waitz.io/live/ucsd-rec"
OUTPUT_CSV = Path(__file__).with_name("ucsd_occupancy_history.csv")
LOG_DIR = Path(__file__).with_name("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"scraper_{datetime.now(ZoneInfo('America/Los_Angeles')).strftime('%Y-%m-%d')}.log"

KNOWN_FACILITIES = {
    "RIMAC Fitness Gym",
    "Main Gym Fitness Gym",
    "Outback Climbing Center",
    "Triton Esports Center",
}


def log(message: str, *, error: bool = False) -> None:
    now = datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] {message}"
    print(line, file=sys.stderr if error else sys.stdout, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def normalize_status(item: Dict[str, object]) -> str:
    loc_html = item.get("locHtml") or {}
    summary = str(loc_html.get("summary") or "").strip()

    if summary:
        if summary.startswith("Not Busy"):
            return "Not Busy"
        if summary.startswith("Active"):
            return "Active"
        if summary.startswith("Busy"):
            return "Busy"
        if summary.startswith("Very Busy"):
            return "Very Active"
        if summary.startswith("Data Unavailable"):
            return "Data Unavailable"
        if summary.startswith("Closed"):
            return "Closed"

    is_open = bool(item.get("isOpen", False))
    is_available = bool(item.get("isAvailable", False))
    percent = int(item.get("busyness", 0) or 0)

    if not is_open:
        return "Closed"
    if not is_available:
        return "Data Unavailable"
    if percent >= 75:
        return "Very Active"
    if percent >= 50:
        return "Busy"
    if percent >= 25:
        return "Active"
    return "Not Busy"


def fetch_waitz_data() -> List[Dict[str, object]]:
    log(f"Fetching {URL}")

    response = requests.get(
        URL,
        timeout=20,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    response.raise_for_status()

    payload = response.json()
    data = payload.get("data", [])

    if not isinstance(data, list):
        raise ValueError("Unexpected response shape: 'data' is not a list")

    return data


def build_rows(data: List[Dict[str, object]]) -> List[Dict[str, object]]:
    now = datetime.now(ZoneInfo("America/Los_Angeles"))
    rows: List[Dict[str, object]] = []

    for item in data:
        facility_name = str(item.get("name") or "").strip()
        if facility_name not in KNOWN_FACILITIES:
            continue

        percent_full = int(item.get("busyness", 0) or 0)
        people = int(item.get("people", 0) or 0)
        capacity = int(item.get("capacity", 0) or 0)
        is_open = bool(item.get("isOpen", False))
        is_available = bool(item.get("isAvailable", False))
        hour_summary = str(item.get("hourSummary") or "").strip() or "unknown"
        loc_html = item.get("locHtml") or {}
        raw_text = str(loc_html.get("summary") or "").strip()
        status = normalize_status(item)

        rows.append(
            {
                "timestamp": now.isoformat(timespec="seconds"),
                "day_of_week": now.strftime("%A"),
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "facility_name": facility_name,
                "status": status,
                "percent_full": percent_full,
                "raw_text": raw_text or status,
                "people": people,
                "capacity": capacity,
                "is_open": is_open,
                "hour_summary": hour_summary,
                "is_data_unavailable": (not is_available) and is_open,
                "is_valid_predictor_row": is_open and is_available and 0 <= percent_full <= 100,
            }
        )

    rows.sort(key=lambda row: row["facility_name"].lower())
    return rows


def append_rows_to_csv(rows: List[Dict[str, object]]) -> None:
    file_exists = OUTPUT_CSV.exists()

    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "timestamp",
                "day_of_week",
                "date",
                "time",
                "facility_name",
                "status",
                "percent_full",
                "raw_text",
                "people",
                "capacity",
                "is_open",
                "hour_summary",
                "is_data_unavailable",
                "is_valid_predictor_row",
            ],
        )

        if not file_exists:
            writer.writeheader()

        writer.writerows(rows)


def main() -> int:
    try:
        log("=== SCRAPE START ===")
        data = fetch_waitz_data()
        rows = build_rows(data)

        if not rows:
            log("No occupancy data found for known facilities.", error=True)
            return 1

        found = {row["facility_name"] for row in rows}
        missing = KNOWN_FACILITIES - found
        if missing:
            log(f"Missing facilities this run: {sorted(missing)}", error=True)

        append_rows_to_csv(rows)

        log(f"Saved {len(rows)} rows to {OUTPUT_CSV.name}")
        for row in rows:
            log(
                f"{row['facility_name']}: {row['percent_full']}% "
                f"({row['status']}) people={row['people']} "
                f"capacity={row['capacity']} is_open={row['is_open']} "
                f"hour_summary={row['hour_summary']}"
            )

        log("=== SCRAPE END OK ===")
        return 0

    except requests.RequestException as e:
        log(f"HTTP ERROR: {e}", error=True)
        tb = traceback.format_exc()
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(tb + "\n")
        print(tb, file=sys.stderr, flush=True)
        return 1

    except Exception as e:
        log(f"SCRAPER ERROR: {e}", error=True)
        tb = traceback.format_exc()
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(tb + "\n")
        print(tb, file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
