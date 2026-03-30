#!/usr/bin/env python3
"""
Scrape UCSD Recreation facility occupancy levels from:
https://recreation.ucsd.edu/facilities/

Uses Playwright for dynamic content.
Appends snapshots to CSV so you can analyze least busy times.
"""

from __future__ import annotations

import csv
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from playwright.sync_api import sync_playwright

URL = "https://recreation.ucsd.edu/facilities/"
OUTPUT_CSV = Path(__file__).with_name("ucsd_occupancy_history.csv")


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_facility_name(name: str) -> str:
    name = clean_text(name)
    name = re.sub(r"^Current Occupancy\s+", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s*-\s*$", "", name)
    return name.strip()


def parse_card_text(card_text: str) -> Optional[Dict[str, object]]:
    text = clean_text(card_text)

    if "% full" not in text:
        return None

    percent_match = re.search(r"(\d+)\s*%\s*full", text, re.IGNORECASE)
    if not percent_match:
        return None
    percent_full = int(percent_match.group(1))

    status = ""
    for candidate in ["Available", "Busy", "Full", "Closed"]:
        if re.search(rf"\b{candidate}\b", text, re.IGNORECASE):
            status = candidate
            break

    # Try to grab facility name before " - Status"
    facility_name = ""
    if status:
        m = re.match(rf"^(.*?)\s*-\s*{status}\b", text, flags=re.IGNORECASE)
        if m:
            facility_name = m.group(1).strip()

    # Fallback: take everything before percent text
    if not facility_name:
        facility_name = text[:percent_match.start()].strip(" -")

    facility_name = normalize_facility_name(facility_name)

    # Reject junk like "23%" or empty strings
    if not facility_name:
        return None
    if re.fullmatch(r"\d+%?", facility_name):
        return None
    if len(facility_name) < 4:
        return None

    return {
        "facility_name": facility_name,
        "status": status or "Unknown",
        "percent_full": percent_full,
        "raw_text": text,
    }


def extract_occupancy_blocks(page) -> List[str]:
    """
    Pull candidate blocks containing occupancy info, then dedupe exact text.
    """
    selectors = [
        "div:has-text('% full')",
        "section:has-text('% full')",
        "article:has-text('% full')",
        "li:has-text('% full')",
    ]

    raw_blocks = []

    for selector in selectors:
        locator = page.locator(selector)
        count = locator.count()
        for i in range(count):
            try:
                txt = clean_text(locator.nth(i).inner_text())
                if "% full" not in txt:
                    continue
                # keep only reasonably sized blocks
                if 10 <= len(txt) <= 160:
                    raw_blocks.append(txt)
            except Exception:
                continue

    # dedupe exact repeated text
    seen = set()
    unique = []
    for block in raw_blocks:
        if block not in seen:
            seen.add(block)
            unique.append(block)

    return unique


def choose_best_rows(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """
    Dedupe by facility name and keep the best-looking row for each facility.
    Prefer rows that:
    - have a real status
    - don't include 'Current Occupancy'
    - have shorter/cleaner raw text
    """
    best_by_facility: Dict[str, Dict[str, object]] = {}

    def score(row: Dict[str, object]) -> tuple:
        raw = str(row["raw_text"])
        status = str(row["status"])
        name = str(row["facility_name"])

        return (
            1 if status != "Unknown" else 0,
            0 if "Current Occupancy" in raw else 1,
            0 if re.fullmatch(r"\d+%?", name) else 1,
            -len(raw),  # shorter is better
        )

    for row in rows:
        key = str(row["facility_name"]).lower()
        if key not in best_by_facility or score(row) > score(best_by_facility[key]):
            best_by_facility[key] = row

    return list(best_by_facility.values())


def scrape_once() -> List[Dict[str, object]]:
    now = datetime.now()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 2200})

        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        blocks = extract_occupancy_blocks(page)
        browser.close()

    parsed_rows = []
    for block in blocks:
        parsed = parse_card_text(block)
        if not parsed:
            continue

        parsed_rows.append(
            {
                "timestamp": now.isoformat(timespec="seconds"),
                "day_of_week": now.strftime("%A"),
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "facility_name": parsed["facility_name"],
                "status": parsed["status"],
                "percent_full": parsed["percent_full"],
                "raw_text": parsed["raw_text"],
            }
        )

    final_rows = choose_best_rows(parsed_rows)

    if not final_rows:
        raise RuntimeError("No occupancy data found — page structure may have changed.")

    return sorted(final_rows, key=lambda r: r["facility_name"].lower())


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