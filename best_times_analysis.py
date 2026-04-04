import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from zoneinfo import ZoneInfo

INPUT_FILE = "ucsd_occupancy_history.csv"
TIMEZONE = ZoneInfo("America/Los_Angeles")

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

    df["percent_full"] = pd.to_numeric(df["percent_full"], errors="coerce")
    df = df.dropna(subset=["percent_full", "facility_name", "time", "day_of_week", "status"])

    df["time"] = df["time"].astype(str).str.strip()
    df["status"] = df["status"].astype(str).str.strip()
    df["raw_text"] = df["raw_text"].fillna("").astype(str).str.strip()

    df["hour"] = pd.to_datetime(df["time"], format="%H:%M:%S", errors="coerce").dt.hour
    df = df.dropna(subset=["hour"])
    df["hour"] = df["hour"].astype(int)

    return df


def filter_good_rows(df):
    # Keep only open rows
    if "is_open" in df.columns:
        df = df[df["is_open"].astype(str).str.lower() == "true"]
    else:
        df = df[df["status"].str.lower() != "closed"]

    # Remove impossible / bad values
    df = df[(df["percent_full"] >= 0) & (df["percent_full"] <= 100)]

    # Remove data-unavailable rows that come through as fake 0%
    bad_raw = df["raw_text"].str.lower().str.contains("data unavailable", na=False)
    df = df[~bad_raw]

    # Remove suspicious 0% rows for facilities that are "open"
    # These have been skewing Triton/RIMAC best-time results.
    df = df[df["percent_full"] > 0]

    return df


def compute_best_times(df):
    grouped = (
        df.groupby(["facility_name", "day_of_week", "hour"])["percent_full"]
        .mean()
        .reset_index()
        .rename(columns={"percent_full": "avg_percent", "day_of_week": "day"})
    )

    grouped["day"] = pd.Categorical(grouped["day"], categories=DAY_ORDER, ordered=True)
    grouped = grouped.sort_values(["avg_percent", "facility_name", "day", "hour"]).reset_index(drop=True)

    return grouped


def save_summary(grouped):
    grouped.to_csv("best_times_summary.csv", index=False)


def save_best_today(grouped):
    today_name = datetime.now(TIMEZONE).strftime("%A")

    if grouped.empty:
        with open("best_time_today.txt", "w", encoding="utf-8") as f:
            f.write(f"No usable occupancy data available yet for {today_name}.")
        return

    today_df = grouped[grouped["day"] == today_name].sort_values("avg_percent")

    if today_df.empty:
        with open("best_time_today.txt", "w", encoding="utf-8") as f:
            f.write(f"No usable occupancy data available yet for {today_name}.")
        return

    best = today_df.iloc[0]

    with open("best_time_today.txt", "w", encoding="utf-8") as f:
        f.write(
            f"Best time today for {best['facility_name']}:\n"
            f"{today_name} at {int(best['hour']):02d}:00\n"
            f"Avg occupancy: {best['avg_percent']:.1f}%"
        )


def generate_charts(df):
    facilities = sorted(df["facility_name"].unique())

    for facility in facilities:
        sub = df[df["facility_name"] == facility].copy()

        hourly = sub.groupby("hour")["percent_full"].mean().sort_index()

        plt.figure(figsize=(8, 4.5))
        hourly.plot(title=f"{facility} Hourly Occupancy")
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
    df = load_data()
    df = filter_good_rows(df)

    grouped = compute_best_times(df)

    save_summary(grouped)
    save_best_today(grouped)
    generate_charts(df)

    print("Analysis complete.")


if __name__ == "__main__":
    main()
