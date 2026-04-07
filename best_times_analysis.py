import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from zoneinfo import ZoneInfo

INPUT_FILE = "ucsd_occupancy_history.csv"
CLEANED_FILE = "ucsd_occupancy_history_cleaned.csv"
TIMEZONE = ZoneInfo("America/Los_Angeles")
MIN_SAMPLES_PER_SLOT = 2
WINDOW_LENGTHS = [3, 4]  # 1.5h and 2h windows using 30-minute buckets
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


def load_data():
    df = pd.read_csv(INPUT_FILE)
    df.columns = df.columns.str.strip()

    required = ["facility_name", "day_of_week", "time", "percent_full", "status", "raw_text"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    for col in ["facility_name", "day_of_week", "time", "status", "raw_text", "hour_summary"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()

    df["facility_name"] = df["facility_name"].astype(str).str.strip()
    df["day_of_week"] = df["day_of_week"].astype(str).str.strip()
    df["time"] = df["time"].astype(str).str.strip()
    df["status"] = df["status"].astype(str).str.strip()
    df["raw_text"] = df["raw_text"].fillna("").astype(str).str.strip()

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    else:
        composed = df["day_of_week"] + " " + df["time"]
        df["timestamp"] = pd.to_datetime(composed, errors="coerce")

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    else:
        df["date"] = df["timestamp"].dt.strftime("%Y-%m-%d")

    df["percent_full"] = pd.to_numeric(df["percent_full"], errors="coerce")
    if "people" in df.columns:
        df["people"] = pd.to_numeric(df["people"], errors="coerce")
    else:
        df["people"] = pd.NA
    if "capacity" in df.columns:
        df["capacity"] = pd.to_numeric(df["capacity"], errors="coerce")
    else:
        df["capacity"] = pd.NA

    if "is_open" in df.columns:
        df["is_open"] = (
            df["is_open"]
            .astype(str)
            .str.strip()
            .str.lower()
            .map({"true": True, "false": False})
        )
    else:
        df["is_open"] = ~df["status"].str.lower().eq("closed")

    parsed_time = pd.to_datetime(df["time"], format="%H:%M:%S", errors="coerce")
    df["hour"] = parsed_time.dt.hour
    df["minute"] = parsed_time.dt.minute
    df = df.dropna(subset=["facility_name", "day_of_week", "timestamp", "hour", "minute"])
    df["hour"] = df["hour"].astype(int)
    df["minute"] = df["minute"].astype(int)

    df["bucket_30_minute"] = ((df["minute"] + 15) // 30) * 30
    overflow = df["bucket_30_minute"] >= 60
    df.loc[overflow, "bucket_30_minute"] = 0
    df.loc[overflow, "hour"] = (df.loc[overflow, "hour"] + 1) % 24
    df["time_bucket_30"] = df["hour"].map(lambda h: f"{h:02d}") + ":" + df["bucket_30_minute"].map(lambda m: f"{int(m):02d}")
    df["bucket_index"] = df["hour"] * 2 + (df["bucket_30_minute"] // 30)

    # Deduplicate exact timestamp/facility collisions.
    df = df.sort_values("timestamp").drop_duplicates(subset=["timestamp", "facility_name"], keep="last")

    return df.reset_index(drop=True)


def clean_data(df):
    df = df.copy()

    raw_lower = df["raw_text"].str.lower()
    status_lower = df["status"].str.lower()
    hour_summary_lower = df.get("hour_summary", pd.Series("", index=df.index)).astype(str).str.lower()

    df["is_data_unavailable"] = (
        raw_lower.str.contains("data unavailable", na=False)
        | hour_summary_lower.str.contains("data unavailable", na=False)
    )

    df["is_valid_percent"] = df["percent_full"].between(0, 100, inclusive="both")
    df["is_valid_predictor_row"] = (
        df["is_open"].fillna(False)
        & ~status_lower.eq("closed")
        & ~df["is_data_unavailable"]
        & df["is_valid_percent"]
        & df["percent_full"].notna()
    )

    # Retain all rows in cleaned CSV, but blank clearly unusable predictor percents.
    df.loc[df["is_data_unavailable"], "percent_full"] = pd.NA

    # Keep stable column order.
    preferred = [
        "timestamp",
        "day_of_week",
        "date",
        "time",
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
        "is_valid_predictor_row",
    ]
    existing = [c for c in preferred if c in df.columns]
    extra = [c for c in df.columns if c not in existing]
    return df[existing + extra]


def predictor_rows(df):
    return df[df["is_valid_predictor_row"]].copy()


def confidence_label(count: int) -> str:
    if count >= 12:
        return "High"
    if count >= 6:
        return "Medium"
    return "Low"


def summarize_time_buckets(df):
    grouped = (
        df.groupby(["facility_name", "day_of_week", "bucket_index", "time_bucket_30"])
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
    grouped = grouped.sort_values(["facility_name", "day_of_week", "bucket_index"]).reset_index(drop=True)
    grouped.rename(columns={"day_of_week": "day"}, inplace=True)
    return grouped


def compute_future_windows(df):
    now = datetime.now(TIMEZONE)
    today = now.strftime("%A")
    current_bucket = now.hour * 2 + (1 if now.minute >= 30 else 0)

    day_specific = summarize_time_buckets(df[df["day_of_week"] == today].copy())
    all_days = (
        df.groupby(["facility_name", "bucket_index", "time_bucket_30"])
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
        all_lookup = {int(r.bucket_index): r for r in all_fac.itertuples(index=False)}

        candidates = []
        for start in range(current_bucket, 48):
            for window_len in WINDOW_LENGTHS:
                indices = list(range(start, min(start + window_len, 48)))
                if len(indices) < 3:
                    continue

                chosen = []
                scope_counts = {"same_day": 0, "all_days": 0}
                enough_same_day = True
                for idx in indices:
                    row = day_lookup.get(idx)
                    if row is not None and int(row.sample_count) >= MIN_SAMPLES_PER_SLOT:
                        chosen.append((row, "same_day"))
                        scope_counts["same_day"] += 1
                        continue
                    enough_same_day = False
                    fallback = all_lookup.get(idx)
                    if fallback is not None and int(fallback.sample_count) >= MIN_SAMPLES_PER_SLOT:
                        chosen.append((fallback, "all_days"))
                        scope_counts["all_days"] += 1
                    else:
                        chosen = []
                        break

                if not chosen:
                    continue

                avg_percent = sum(float(r.avg_percent) for r, _ in chosen) / len(chosen)
                peak_percent = max(float(r.p75_percent) if pd.notna(r.p75_percent) else float(r.avg_percent) for r, _ in chosen)
                sample_floor = min(int(r.sample_count) for r, _ in chosen)
                sample_total = sum(int(r.sample_count) for r, _ in chosen)
                fallback_penalty = scope_counts["all_days"] * 4.0
                short_window_penalty = 1.5 if len(chosen) == 3 else 0
                sample_bonus = min(sample_total, 40) * 0.08
                near_future_bonus = max(0, 2 - (start - current_bucket) * 0.2)
                score = avg_percent + peak_percent * 0.35 + fallback_penalty + short_window_penalty - sample_bonus - near_future_bonus
                source_scope = "same_day" if enough_same_day else ("mixed" if scope_counts["same_day"] else "all_days")
                confidence = confidence_label(sample_floor)
                candidates.append(
                    {
                        "facility_name": facility,
                        "day": today,
                        "start_bucket": start,
                        "start_time": f"{start // 2:02d}:{'30' if start % 2 else '00'}",
                        "end_time": f"{(indices[-1] // 2):02d}:{'30' if indices[-1] % 2 else '00'}",
                        "window_minutes": len(indices) * 30,
                        "window_label": " -> ".join(f"{idx // 2:02d}:{'30' if idx % 2 else '00'}" for idx in indices),
                        "avg_percent": round(avg_percent, 2),
                        "peak_percent": round(peak_percent, 2),
                        "sample_floor": sample_floor,
                        "sample_total": sample_total,
                        "confidence": confidence,
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


def save_summary(grouped):
    grouped.to_csv("best_times_summary.csv", index=False)


def save_cleaned_csv(df):
    out = df.copy()
    if "timestamp" in out.columns:
        out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce").dt.strftime("%Y-%m-%dT%H:%M:%S%z")
        out["timestamp"] = out["timestamp"].str.replace(r"([+-]\d{2})(\d{2})$", r"\1:\2", regex=True)
    out.to_csv(CLEANED_FILE, index=False)


def save_best_today(windows):
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


def generate_charts(df):
    facilities = sorted(df["facility_name"].unique())

    for facility in facilities:
        sub = df[df["facility_name"] == facility].copy()
        if sub.empty:
            continue

        hourly = (
            sub.groupby("hour")
            .agg(
                avg_percent=("percent_full", "mean"),
                sample_count=("percent_full", "count"),
            )
            .reset_index()
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
            aggfunc="mean"
        )

        heat = heat.reindex([d for d in DAY_ORDER if d in heat.index])

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


def main():
    raw = load_data()
    cleaned = clean_data(raw)
    usable = predictor_rows(cleaned)

    summary = summarize_time_buckets(usable)
    save_summary(summary)
    save_cleaned_csv(cleaned)

    windows = compute_future_windows(usable)
    windows.to_csv("next_best_windows_today.csv", index=False)
    save_best_today(windows)
    generate_charts(usable)

    print("Analysis complete.")


if __name__ == "__main__":
    main()
