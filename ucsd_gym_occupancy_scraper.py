#!/usr/bin/env python3
"""
Scrape UCSD Recreation facility occupancy levels from:
https://recreation.ucsd.edu/facilities/

Designed to be more reliable both locally and in GitHub Actions.
If no occupancy data is found, this script exits cleanly without changing the CSV.
"""

from __future__ import annotations

import csv
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

URL = "https://recreation.ucsd.edu/facilities/"
OUTPUT_CSV = Path(__file__).with_name("ucsd_occupancy_history.csv")

KNOWN_FACILITIES = {
    "rimac fitness gym",
    "main gym fitness gym",
    "outback climbing center",
    "triton esports center",
}

VALID_STATUSES = {"available", "busy", "full", "closed", "active"}


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_facility_name(name: str) -> str:
    name = clean_text(name)
    name = re.sub(r"^Current Occupancy\s+", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s*-\s*$", "", name)
    return name.strip()


def parse_card_text(card_text: str) -> Optional[Dict[str, object]]:
    text = clean_text(card_text)

    status = ""
    for candidate in ["Available", "Busy", "Full", "Closed", "Active"]:
        if re.search(rf"\b{candidate}\b", text, re.IGNORECASE):
            status = candidate
            break

    percent_match = re.search(r"(\d+)\s*%\s*full", text, re.IGNORECASE)
    percent_full = int(percent_match.group(1)) if percent_match else None

    facility_name = ""
    if status:
        parts = re.split(rf"\s*-\s*{status}\b", text, flags=re.IGNORECASE)
        if parts and parts[0].strip():
            facility_name = parts[0].strip()

    if not facility_name:
        # fallback: everything before percent
        if percent_match:
            facility_name = text[:percent_match.start()].strip(" -")

    if not facility_name:
        return None

    facility_name = normalize_facility_name(facility_name)
    facility_key = facility_name.lower()

    if facility_key not in KNOWN_FACILITIES:
        return None

    return {
        "facility_name": facility_name,
        "facility_key": facility_key,
        "status": status or "Unknown",
        "percent_full": percent_full if percent_full is not None else 0,
        "raw_text": text,
    }


def extract_candidate_blocks(page) -> List[str]:
    """
    Use the actual occupancy container structure from the page:
    #waitzLiveList contains one bordered <div> per facility card.
    """
    raw_blocks: List[str] = []

    selectors = [
        "#waitzLiveList > div",
        "#waitzLiveList div[style*='border: 2px solid']",
    ]

    for selector in selectors:
        locator = page.locator(selector)
        try:
            count = locator.count()
        except Exception:
            continue

        for i in range(count):
            try:
                txt = clean_text(locator.nth(i).inner_text(timeout=1000))
            except Exception:
                continue

            lowered = txt.lower()
            has_percent = "% full" in lowered
            has_status = any(status in lowered for status in VALID_STATUSES)

            if not has_status:
                continue

            # Only keep realistic card-sized blocks
            if 10 <= len(txt) <= 220:
                raw_blocks.append(txt)

    seen = set()
    unique = []
    for block in raw_blocks:
        if block not in seen:
            seen.add(block)
            unique.append(block)

    return unique


def score_row(row: Dict[str, object]) -> tuple:
    raw = str(row["raw_text"])
    status = str(row["status"]).lower()
    name = str(row["facility_name"]).lower()

    return (
        1 if name in KNOWN_FACILITIES else 0,
        1 if status in VALID_STATUSES else 0,
        1 if status in {"available", "active", "busy", "full", "closed"} else 0,
        0 if "Current Occupancy" in raw else 1,
        -len(raw),
    )


def choose_best_rows(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    best_by_facility: Dict[str, Dict[str, object]] = {}

    for row in rows:
        key = str(row["facility_key"])
        if key not in best_by_facility or score_row(row) > score_row(best_by_facility[key]):
            best_by_facility[key] = row

    chosen = list(best_by_facility.values())
    return sorted(chosen, key=lambda r: str(r["facility_name"]).lower())


def scrape_once() -> List[Dict[str, object]]:
    now = datetime.now(ZoneInfo("America/Los_Angeles"))

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )
        page = browser.new_page(viewport={"width": 1440, "height": 2400})

        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)

        parsed_rows: List[Dict[str, object]] = []

        for _ in range(4):
            candidate_blocks = extract_candidate_blocks(page)

            parsed_rows = []
            for block in candidate_blocks:
                parsed = parse_card_text(block)
                if parsed:
                    parsed_rows.append(parsed)

            chosen = choose_best_rows(parsed_rows)
            found_known = {str(r["facility_key"]) for r in chosen} & KNOWN_FACILITIES

            # We want all four if possible, but at least RIMAC + Main Gym
            if "rimac fitness gym" in found_known and "main gym fitness gym" in found_known:
                parsed_rows = chosen
                break

            page.wait_for_timeout(1500)

        browser.close()

    final_rows = choose_best_rows(parsed_rows)

    if not final_rows:
        return []

    rows = []
    for row in final_rows:
        rows.append(
            {
                "timestamp": now.isoformat(timespec="seconds"),
                "day_of_week": now.strftime("%A"),
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "facility_name": row["facility_name"],
                "status": row["status"],
                "percent_full": row["percent_full"],
                "raw_text": row["raw_text"],
            }
        )

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
            ],
        )

        if not file_exists:
            writer.writeheader()

        for row in rows:
            writer.writerow(row)


def main() -> int:
    try:
        rows = scrape_once()

        if not rows:
            print("WARNING: No occupancy data found. Skipping this run without changing the CSV.")
            return 0

        append_rows_to_csv(rows)

        print(f"Saved {len(rows)} rows to {OUTPUT_CSV.name}")
        for row in rows:
            print(f"{row['facility_name']}: {row['percent_full']}% ({row['status']})")
        return 0

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
