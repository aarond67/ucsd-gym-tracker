#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

TARGET_FACILITIES = {
    "Main Gym Fitness Gym",
    "RIMAC Fitness Gym",
}

WEEKEND_CLOSED_FACILITIES = {
    "Outback Climbing Center",
    "Triton Esports Center",
}

CLOSED_WORDS = {"closed"}


@dataclass
class NormalizedRow:
    timestamp: str
    day_of_week: str
    date: str
    time: str
    facility_name: str
    status: str
    percent_full: int
    raw_text: str
    people: int
    capacity: int
    is_open: bool
    hour_summary: str
    is_data_unavailable: bool
    is_valid_percent: bool
    predictor_exclusion_reason: str
    is_valid_predictor_row: bool
    hour: int
    minute: int
    time_bucket_15: str
    bucket_index_15: int
    bucket_15_minute: int
    time_bucket_30: str
    bucket_index: int
    bucket_30_minute: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean UCSD gym history and produce predictor-ready 15-minute aggregates.")
    parser.add_argument("--input", default="ucsd_occupancy_history.csv", help="Raw scrape CSV path")
    parser.add_argument(
        "--cleaned-output",
        default="ucsd_occupancy_history_cleaned.csv",
        help="Row-level cleaned CSV path",
    )
    parser.add_argument(
        "--predictor-output",
        default="ucsd_occupancy_predictor_15min.csv",
        help="15-minute aggregated predictor CSV path",
    )
    parser.add_argument(
        "--keep-all-facilities",
        action="store_true",
        help="Keep Outback and Triton in outputs instead of restricting to Main/RIMAC in predictor files.",
    )
    return parser.parse_args()


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"true", "1", "yes", "y"}


def as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(round(float(str(value).strip())))
    except Exception:
        return default


def derive_time_parts(timestamp: str, date_str: str, time_str: str) -> tuple[str, str, str, int, int]:
    dt: datetime | None = None
    if timestamp:
        try:
            dt = datetime.fromisoformat(timestamp)
        except Exception:
            dt = None
    if dt is None and date_str and time_str:
        try:
            dt = datetime.fromisoformat(f"{date_str}T{time_str}")
        except Exception:
            dt = None
    if dt is None:
        raise ValueError(f"Could not parse row time from timestamp={timestamp!r} date={date_str!r} time={time_str!r}")
    return dt.date().isoformat(), dt.strftime("%A"), dt.strftime("%H:%M:%S"), dt.hour, dt.minute


def bucket_label(bucket_index: int, size_minutes: int) -> tuple[str, int]:
    total_minutes = bucket_index * size_minutes
    hour = total_minutes // 60
    minute = total_minutes % 60
    return f"{hour:02d}:{minute:02d}", minute


def normalize_status(percent_full: int, is_open: bool, raw_text: str, original_status: str) -> str:
    if not is_open:
        return "Closed"
    raw_lower = (raw_text or "").lower()
    if "data unavailable" in raw_lower:
        return "Data Unavailable"
    if percent_full < 30:
        return "Not Busy"
    if percent_full < 60:
        return "Active"
    if percent_full < 80:
        return "Busy"
    return "Very Active"


def normalize_row(row: dict[str, Any], keep_all_facilities: bool) -> NormalizedRow | None:
    facility_name = str(row.get("facility_name", "")).strip()
    if not facility_name:
        return None

    if not keep_all_facilities and facility_name not in TARGET_FACILITIES:
        # still allow row-level cleaned history for debugging of all facilities?
        # User asked to fix Outback/Triton weekend behavior, so keep them in cleaned output only when keep_all is on.
        # By default, predictor-focused outputs should only carry Main/RIMAC.
        return None

    timestamp = str(row.get("timestamp", "")).strip()
    date_str = str(row.get("date", "")).strip()
    time_str = str(row.get("time", "")).strip()
    date_str, day_of_week, time_str, hour, minute = derive_time_parts(timestamp, date_str, time_str)

    raw_text = str(row.get("raw_text", "")).strip()
    hour_summary = str(row.get("hour_summary", "")).strip() or "open"
    status_in = str(row.get("status", "")).strip()

    people = as_int(row.get("people"), 0)
    capacity = max(as_int(row.get("capacity"), 0), 0)
    percent_full = as_int(row.get("percent_full"), 0)
    is_open = as_bool(row.get("is_open"))
    is_data_unavailable = as_bool(row.get("is_data_unavailable")) or ("data unavailable" in raw_text.lower())

    # Force known weekend closures for facilities that should not be open.
    if facility_name in WEEKEND_CLOSED_FACILITIES and day_of_week in {"Saturday", "Sunday"}:
        is_open = False
        people = 0
        percent_full = 0
        status_in = "Closed"
        hour_summary = "Closed"
        predictor_exclusion_reason = "forced_weekend_closed"
    else:
        predictor_exclusion_reason = "ok"

    # Normalize all closed rows.
    status_lower = status_in.lower()
    if (not is_open) or status_lower in CLOSED_WORDS or raw_text.lower() == "closed":
        is_open = False
        people = 0
        percent_full = 0
        status_in = "Closed"
        if predictor_exclusion_reason == "ok":
            predictor_exclusion_reason = "closed"

    # Capacity/percent handling.
    if capacity > 0:
        derived_percent = round((people / capacity) * 100)
        # Preserve real overflow counts instead of clamping people to capacity.
        percent_full = max(0, derived_percent)
        is_valid_percent = percent_full >= 0
    else:
        is_valid_percent = False
        if predictor_exclusion_reason == "ok":
            predictor_exclusion_reason = "invalid_capacity"

    if is_data_unavailable and predictor_exclusion_reason == "ok":
        predictor_exclusion_reason = "data_unavailable"
    if not is_valid_percent and predictor_exclusion_reason == "ok":
        predictor_exclusion_reason = "invalid_percent"

    is_valid_predictor_row = (
        predictor_exclusion_reason == "ok"
        and is_open
        and not is_data_unavailable
        and capacity > 0
        and percent_full >= 0
    )

    status = normalize_status(percent_full, is_open, raw_text, status_in)

    bucket_index_15 = (hour * 60 + minute) // 15
    time_bucket_15, bucket_15_minute = bucket_label(bucket_index_15, 15)
    bucket_index_30 = (hour * 60 + minute) // 30
    time_bucket_30, bucket_30_minute = bucket_label(bucket_index_30, 30)

    return NormalizedRow(
        timestamp=timestamp,
        day_of_week=day_of_week,
        date=date_str,
        time=time_str,
        facility_name=facility_name,
        status=status,
        percent_full=percent_full,
        raw_text=raw_text,
        people=people,
        capacity=capacity,
        is_open=is_open,
        hour_summary=hour_summary,
        is_data_unavailable=is_data_unavailable,
        is_valid_percent=is_valid_percent,
        predictor_exclusion_reason=predictor_exclusion_reason,
        is_valid_predictor_row=is_valid_predictor_row,
        hour=hour,
        minute=minute,
        time_bucket_15=time_bucket_15,
        bucket_index_15=bucket_index_15,
        bucket_15_minute=bucket_15_minute,
        time_bucket_30=time_bucket_30,
        bucket_index=bucket_index_30,
        bucket_30_minute=bucket_30_minute,
    )


def write_cleaned(rows: list[NormalizedRow], path: Path) -> None:
    fieldnames = [
        "timestamp",
        "day_of_week",
        "date",
        "time",
        "time_bucket_15",
        "bucket_index_15",
        "time_bucket_30",
        "bucket_index",
        "facility_name",
        "status",
        "percent_full",
        "raw_text",
        "people",
        "capacity",
        "is_open",
        "hour_summary",
        "is_data_unavailable",
        "is_valid_percent",
        "predictor_exclusion_reason",
        "is_valid_predictor_row",
        "hour",
        "minute",
        "bucket_15_minute",
        "bucket_30_minute",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)


def aggregate_predictor(rows: list[NormalizedRow]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, int], list[NormalizedRow]] = defaultdict(list)
    for row in rows:
        if not row.is_valid_predictor_row:
            continue
        grouped[(row.facility_name, row.date, row.bucket_index_15)].append(row)

    aggregated: list[dict[str, Any]] = []
    for (facility_name, date_str, bucket_index_15), group in sorted(grouped.items()):
        first = sorted(group, key=lambda r: r.timestamp)[0]
        avg_percent = round(sum(r.percent_full for r in group) / len(group), 2)
        avg_people = round(sum(r.people for r in group) / len(group), 2)
        aggregated.append(
            {
                "facility_name": facility_name,
                "date": date_str,
                "day_of_week": first.day_of_week,
                "bucket_index_15": bucket_index_15,
                "time_bucket_15": first.time_bucket_15,
                "bucket_15_minute": first.bucket_15_minute,
                "avg_percent_full": avg_percent,
                "avg_people": avg_people,
                "capacity": first.capacity,
                "sample_count_within_bucket": len(group),
                "source_first_timestamp": first.timestamp,
            }
        )
    return aggregated


def write_predictor(rows: list[dict[str, Any]], path: Path) -> None:
    fieldnames = [
        "facility_name",
        "date",
        "day_of_week",
        "bucket_index_15",
        "time_bucket_15",
        "bucket_15_minute",
        "avg_percent_full",
        "avg_people",
        "capacity",
        "sample_count_within_bucket",
        "source_first_timestamp",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    cleaned_path = Path(args.cleaned_output)
    predictor_path = Path(args.predictor_output)

    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    normalized_rows: list[NormalizedRow] = []
    with input_path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for raw_row in reader:
            row = normalize_row(raw_row, keep_all_facilities=args.keep_all_facilities)
            if row is not None:
                normalized_rows.append(row)

    normalized_rows.sort(key=lambda r: (r.timestamp, r.facility_name))
    write_cleaned(normalized_rows, cleaned_path)
    predictor_rows = aggregate_predictor(normalized_rows)
    write_predictor(predictor_rows, predictor_path)

    print(f"Wrote cleaned history: {cleaned_path} ({len(normalized_rows)} rows)")
    print(f"Wrote predictor 15-min data: {predictor_path} ({len(predictor_rows)} rows)")


if __name__ == "__main__":
    main()
