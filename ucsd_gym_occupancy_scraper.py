#!/usr/bin/env python3
"""
Fetch UCSD gym occupancy directly from the Waitz API and append results to CSV.
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

URL = "https://waitz.io/live/ucsd-rec"
OUTPUT_CSV = Path(__file__).with_name("ucsd_occupancy_history.csv")
TIMEZONE = ZoneInfo("America/Los_Angeles")

FIELDNAMES = [
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
]

KNOWN_FACILITIES = {
    "RIMAC Fitness Gym",
    "Main Gym Fitness Gym",
    "Outback Climbing Center",
    "Triton Esports Center",
}


def derive_status(busyness: int, is_open: bool) -> str:
    if not is_open:
        return "Closed"
    if busyness >= 75:
        return "Very Active"
    if busyness >= 50:
        return "Busy"
    if busyness >= 25:
        return "Active"
    return "Not Busy"


def fetch_waitz_data() -> list[dict]:
    response = requests.get(
        URL,
        timeout=20,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        },
    )
    response.raise_for_status()

    payload = response.json()
    data = payload.get("data", [])

    if not isinstance(data, list):
        raise ValueError("Unexpected API response format")

    return data


def build_rows(data: list[dict]) -> list[dict]:
    now = datetime.now(TIMEZONE)
    timestamp = now.isoformat(timespec="seconds")

    rows = []

    for facility in data:
        name = str(facility.get("name", "")).strip()
        if name not in KNOWN_FACILITIES:
            continue

        is_open = bool(facility.get("isOpen", False))
        busyness = int(facility.get("busyness", 0) or 0)
        people = int(facility.get("people", 0) or 0)
        capacity = int(facility.get("capacity", 0) or 0)
        hour_summary = str(facility.get("hourSummary", "") or "").strip()

        loc_html = facility.get("locHtml", {}) or {}
        raw_text = str(loc_html.get("summary", "") or "").strip()

        if not raw_text:
            raw_text = f"{name} - {busyness}% full"

        rows.append(
            {
                "timestamp": timestamp,
                "day_of_week": now.strftime("%A"),
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "facility_name": name,
                "status": derive_status(busyness, is_open),
                "percent_full": busyness,
                "raw_text": raw_text,
                "people": people,
                "capacity": capacity,
                "is_open": is_open,
                "hour_summary": hour_summary,
            }
        )

    return sorted(rows, key=lambda r: r["facility_name"])


def append_rows(rows: list[dict]) -> None:
    expected_header = ",".join(FIELDNAMES)
    needs_reset = True

    if OUTPUT_CSV.exists() and OUTPUT_CSV.stat().st_size > 0:
        with OUTPUT_CSV.open("r", encoding="utf-8") as f:
            first_line = f.readline().strip()
            if first_line == expected_header:
                needs_reset = False

    mode = "w" if needs_reset else "a"

    with OUTPUT_CSV.open(mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)

        if needs_reset:
            writer.writeheader()
            print("Reset CSV with correct header")

        writer.writerows(rows)


def main():
    try:
        data = fetch_waitz_data()
        rows = build_rows(data)

        if not rows:
            print("No data found")
            return

        found = {r["facility_name"] for r in rows}
        missing = KNOWN_FACILITIES - found
        if missing:
            print("Warning: missing facilities:", missing)

        append_rows(rows)
        print(f"Wrote {len(rows)} rows")

    except Exception as e:
        print("Error:", e)


if __name__ == "__main__":
    main()
