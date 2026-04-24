import os
from datetime import datetime
from zoneinfo import ZoneInfo

import matplotlib.pyplot as plt
import pandas as pd

CLEANED_FILE = "ucsd_occupancy_history_cleaned.csv"
PREDICTOR_FILE = "ucsd_occupancy_predictor_15min.csv"
TIMEZONE = ZoneInfo("America/Los_Angeles")
MIN_SAMPLES_PER_SLOT = 2
WINDOW_LENGTHS = [6, 8]  # 90 min and 120 min windows using 15-minute buckets
TARGET_FACILITIES = ["Main Gym Fitness Gym", "RIMAC Fitness Gym"]

DAY_ORDER = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def as_bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.astype(str).str.strip().str.lower().map({"true": True, "false": False}).fillna(False)


def confidence_label(count: int) -> str:
    if count >= 12:
        return "High"
    if count >= 6:
        return "Medium"
    return "Low"


def bucket_to_label(bucket_index_15: int) -> str:
    total_minutes = int(bucket_index_15) * 15
    hour = total_minutes // 60
    minute = total_minutes % 60
    return f"{hour:02d}:{minute:02d}"


def load_cleaned_data() -> pd.DataFrame:
    if not os.path.exists(CLEANED_FILE):
        raise FileNotFoundError(
            f"{CLEANED_FILE} not found. Run clean_gym_history_patched.py before best_times_analysis.py."
        )

    df = pd.read_csv(CLEANED_FILE)
    df.columns = df.columns.str.strip()

    required = [
        "facility_name",
        "day_of_week",
        "date",
        "time",
        "percent_full",
        "is_valid_predictor_row",
        "hour",
    ]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required cleaned CSV columns: {missing}")

    for col in ["facility_name", "day_of_week", "date", "time", "status", "raw_text"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()

    df["percent_full"] = pd.to_numeric(df["percent_full"], errors="coerce")
    df["hour"] = pd.to_numeric(df["hour"], errors="coerce")
    df["is_valid_predictor_row"] = as_bool_series(df["is_valid_predictor_row"])

    if "bucket_index_15" in df.columns:
        df["bucket_index_15"] = pd.to_numeric(df["bucket_index_15"], errors="coerce")
    if "time_bucket_15" not in df.columns and "bucket_index_15" in df.columns:
        df["time_bucket_15"] = df["bucket_index_15"].apply(lambda value: bucket_to_label(int(value)) if pd.notna(value) else "")

    return df.dropna(subset=["facility_name", "day_of_week", "percent_full", "hour"]).reset_index(drop=True)


def load_predictor_data() -> pd.DataFrame:
    if not os.path.exists(PREDICTOR_FILE):
        raise FileNotFoundError(
            f"{PREDICTOR_FILE} not found. Run clean_gym_history_patched.py before best_times_analysis.py."
        )

    df = pd.read_csv(PREDICTOR_FILE)
    df.columns = df.columns.str.strip()

    required = ["facility_name", "date", "day_of_week", "bucket_index_15", "time_bucket_15"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required predictor CSV columns: {missing}")

    if "avg_percent_full" in df.columns:
        df["percent_full"] = pd.to_numeric(df["avg_percent_full"], errors="coerce")
    elif "percent_full" in df.columns:
        df["percent_full"] = pd.to_numeric(df["percent_full"], errors="coerce")
    else:
        raise ValueError("Predictor CSV needs avg_percent_full or percent_full.")

    for col in ["facility_name", "day_of_week", "date", "time_bucket_15"]:
        df[col] = df[col].fillna("").astype(str).str.strip()

    df["bucket_index_15"] = pd.to_numeric(df["bucket_index_15"], errors="coerce")
    if "sample_count_within_bucket" in df.columns:
        df["sample_count_within_bucket"] = pd.to_numeric(df["sample_count_within_bucket"], errors="coerce").fillna(1)
    else:
        df["sample_count_within_bucket"] = 1

    return df.dropna(subset=["facility_name", "day_of_week", "bucket_index_15", "percent_full"]).reset_index(drop=True)


def summarize_time_buckets(df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        df.groupby(["facility_name", "day_of_week", "bucket_index_15", "time_bucket_15"])
        .agg(
            avg_percent=("percent_full", "mean"),
            sample_count=("percent_full", "count"),
            median_percent=("percent_full", "median"),
            p75_percent=("percent_full", lambda s: s.quantile(0.75)),
        )
        .reset_index()
    )
    grouped["confidence"] = grouped["sample_count"].apply(confidence_label)
    grouped["day_of_week"] = pd.Categorical(grouped["day_of_week"], categories=DAY_ORDER, ordered=True)
    grouped = grouped.sort_values(["facility_name", "day_of_week", "bucket_index_15"]).reset_index(drop=True)
    grouped.rename(
        columns={
            "day_of_week": "day",
            "bucket_index_15": "bucket_index",
            "time_bucket_15": "time_bucket_15",
        },
        inplace=True,
    )
    return grouped


def compute_future_windows(df: pd.DataFrame) -> pd.DataFrame:
    now = datetime.now(TIMEZONE)
    today = now.strftime("%A")
    current_bucket = now.hour * 4 + (now.minute // 15)
    if now.minute % 15 != 0:
        current_bucket += 1
    current_bucket = min(current_bucket, 95)

    day_specific = summarize_time_buckets(df[df["day_of_week"] == today].copy())
    all_days = (
        df.groupby(["facility_name", "bucket_index_15", "time_bucket_15"])
        .agg(
            avg_percent=("percent_full", "mean"),
            sample_count=("percent_full", "count"),
            median_percent=("percent_full", "median"),
            p75_percent=("percent_full", lambda s: s.quantile(0.75)),
        )
        .reset_index()
    )
    all_days["confidence"] = all_days["sample_count"].apply(confidence_label)

    rows = []
    for facility in TARGET_FACILITIES:
        day_fac = day_specific[day_specific["facility_name"] == facility].copy()
        all_fac = all_days[all_days["facility_name"] == facility].copy()

        day_lookup = {int(r.bucket_index): r for r in day_fac.itertuples(index=False)}
        all_lookup = {int(r.bucket_index_15): r for r in all_fac.itertuples(index=False)}

        candidates = []
        for start in range(current_bucket, 96):
            for window_len in WINDOW_LENGTHS:
                indices = list(range(start, start + window_len))
                if indices[-1] >= 96:
                    continue

                chosen = []
                scope_counts = {"same_day": 0, "all_days": 0}
                for idx in indices:
                    row = day_lookup.get(idx)
                    if row is not None and int(row.sample_count) >= MIN_SAMPLES_PER_SLOT:
                        chosen.append((row, "same_day"))
                        scope_counts["same_day"] += 1
                        continue

                    fallback = all_lookup.get(idx)
                    if fallback is not None and int(fallback.sample_count) >= MIN_SAMPLES_PER_SLOT:
                        chosen.append((fallback, "all_days"))
                        scope_counts["all_days"] += 1
                    else:
                        chosen = []
                        break

                if len(chosen) != window_len:
                    continue

                avg_percent = sum(float(r.avg_percent) for r, _ in chosen) / len(chosen)
                peak_percent = max(
                    float(r.p75_percent) if pd.notna(r.p75_percent) else float(r.avg_percent)
                    for r, _ in chosen
                )
                sample_floor = min(int(r.sample_count) for r, _ in chosen)
                sample_total = sum(int(r.sample_count) for r, _ in chosen)
                fallback_penalty = scope_counts["all_days"] * 4.0
                sample_bonus = min(sample_total, 40) * 0.08
                near_future_bonus = max(0, 2 - (start - current_bucket) * 0.05)
                score = avg_percent + peak_percent * 0.35 + fallback_penalty - sample_bonus - near_future_bonus

                if scope_counts["same_day"] == window_len:
                    source_scope = "same_day"
                elif scope_counts["same_day"] == 0:
                    source_scope = "all_days"
                else:
                    source_scope = "mixed"

                end_bucket_exclusive = indices[-1] + 1
                candidates.append(
                    {
                        "facility_name": facility,
                        "day": today,
                        "start_bucket": start,
                        "start_time": bucket_to_label(start),
                        "end_time": bucket_to_label(end_bucket_exclusive) if end_bucket_exclusive < 96 else "24:00",
                        "window_minutes": len(indices) * 15,
                        "window_label": " -> ".join(bucket_to_label(idx) for idx in indices),
                        "avg_percent": round(avg_percent, 2),
                        "peak_percent": round(peak_percent, 2),
                        "sample_floor": sample_floor,
                        "sample_total": sample_total,
                        "confidence": confidence_label(sample_floor),
                        "source_scope": source_scope,
                        "score": round(score, 3),
                    }
                )

        candidates_df = pd.DataFrame(candidates)
        if candidates_df.empty:
            rows.append(
                {
                    "facility_name": facility,
                    "day": today,
                    "start_bucket": pd.NA,
                    "start_time": "",
                    "end_time": "",
                    "window_minutes": pd.NA,
                    "window_label": "No future data-backed window left today",
                    "avg_percent": pd.NA,
                    "peak_percent": pd.NA,
                    "sample_floor": pd.NA,
                    "sample_total": pd.NA,
                    "confidence": "N/A",
                    "source_scope": "none",
                    "score": pd.NA,
                }
            )
            continue

        candidates_df = candidates_df.sort_values(["score", "avg_percent", "peak_percent", "start_bucket"]).reset_index(drop=True)
        rows.append(candidates_df.iloc[0].to_dict())

    return pd.DataFrame(rows)


def save_summary(grouped: pd.DataFrame) -> None:
    grouped.to_csv("best_times_summary.csv", index=False)


def save_best_today(windows: pd.DataFrame) -> None:
    if windows.empty:
        text = "No usable occupancy data available yet today."
    else:
        parts = []
        for row in windows.itertuples(index=False):
            if pd.isna(row.avg_percent):
                parts.append(f"{row.facility_name}: No future data-backed window left today.")
                continue
            parts.append(
                f"{row.facility_name}: {row.start_time} for {int(row.window_minutes)} min "
                f"(~{row.avg_percent:.1f}% avg, ~{row.peak_percent:.1f}% peak, {row.source_scope}, {row.confidence} confidence)"
            )
        text = "\n".join(parts)

    with open("best_time_today.txt", "w", encoding="utf-8") as f:
        f.write(text)


def generate_charts(df: pd.DataFrame) -> None:
    chart_df = df[
        (df["is_valid_predictor_row"])
        & (df["facility_name"].isin(TARGET_FACILITIES))
        & (df["percent_full"].notna())
    ].copy()

    for facility in TARGET_FACILITIES:
        sub = chart_df[chart_df["facility_name"] == facility].copy()
        if sub.empty:
            continue

        hourly = (
            sub.groupby("hour")
            .agg(
                avg_percent=("percent_full", "mean"),
                sample_count=("percent_full", "count"),
            )
            .reset_index()
            .sort_values("hour")
        )

        plt.figure(figsize=(8, 4.5))
        plt.plot(hourly["hour"], hourly["avg_percent"])
        plt.title(f"{facility} Hourly Occupancy")
        plt.ylabel("Percent Full")
        plt.xlabel("Hour")
        plt.tight_layout()
        plt.savefig(f"{facility.replace(' ', '_')}_hourly.png")
        plt.close()

        heat = sub.pivot_table(
            index="day_of_week",
            columns="hour",
            values="percent_full",
            aggfunc="mean",
        )
        heat = heat.reindex([d for d in DAY_ORDER if d in heat.index])

        if heat.empty:
            continue

        plt.figure(figsize=(10, 4.5))
        plt.imshow(heat, aspect="auto")
        plt.colorbar(label="Percent Full")
        plt.title(f"{facility} Heatmap")
        plt.ylabel("Day")
        plt.xlabel("Hour")
        plt.yticks(range(len(heat.index)), heat.index)
        plt.xticks(range(len(heat.columns)), heat.columns)
        plt.tight_layout()
        plt.savefig(f"{facility.replace(' ', '_')}_heatmap.png")
        plt.close()


def main() -> None:
    cleaned = load_cleaned_data()
    predictor = load_predictor_data()

    summary = summarize_time_buckets(predictor)
    save_summary(summary)

    windows = compute_future_windows(predictor)
    windows.to_csv("next_best_windows_today.csv", index=False)
    save_best_today(windows)

    generate_charts(cleaned)

    print("Analysis complete.")
    print(f"Read charts from {CLEANED_FILE}")
    print(f"Read summaries/windows from {PREDICTOR_FILE}")


if __name__ == "__main__":
    main()
