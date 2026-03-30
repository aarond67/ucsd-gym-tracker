import matplotlib
matplotlib.use("Agg")

import pandas as pd
import matplotlib.pyplot as plt

CSV_FILE = "ucsd_occupancy_history.csv"

df = pd.read_csv(CSV_FILE)

# Parse timestamps with timezone preserved
df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
df = df.dropna(subset=["timestamp", "percent_full", "facility_name"]).copy()

df["percent_full"] = pd.to_numeric(df["percent_full"], errors="coerce")
df = df.dropna(subset=["percent_full"]).copy()

df["status"] = df["status"].fillna("").astype(str).str.lower()
df["hour"] = df["timestamp"].dt.tz_convert("America/Los_Angeles").dt.hour
df["day"] = df["timestamp"].dt.tz_convert("America/Los_Angeles").dt.day_name()

day_order = [
    "Monday", "Tuesday", "Wednesday",
    "Thursday", "Friday", "Saturday", "Sunday"
]

analysis_df = df[df["status"] != "closed"].copy()

if analysis_df.empty:
    print("No open-gym occupancy rows available for analysis.")
    pd.DataFrame(columns=["facility_name", "day", "hour", "avg_percent"]).to_csv(
        "best_times_summary.csv", index=False
    )

    today_name = pd.Timestamp.now(tz="America/Los_Angeles").day_name()
    with open("best_time_today.txt", "w") as f:
        f.write(
            f"Best gym times for {today_name}\n\n"
            "No open-gym occupancy data is available yet.\n"
        )

    print("Saved empty best_times_summary.csv and fallback best_time_today.txt")
    raise SystemExit(0)

summary = (
    analysis_df.groupby(["facility_name", "day", "hour"])["percent_full"]
    .mean()
    .reset_index()
    .rename(columns={"percent_full": "avg_percent"})
)

summary["day"] = pd.Categorical(summary["day"], categories=day_order, ordered=True)
summary = summary.sort_values(["facility_name", "avg_percent", "day", "hour"])

top_rows = []
for facility in summary["facility_name"].unique():
    top10 = summary[summary["facility_name"] == facility].head(10).copy()
    top_rows.append(top10)

best_times = pd.concat(top_rows, ignore_index=True) if top_rows else pd.DataFrame()
best_times.to_csv("best_times_summary.csv", index=False)

print("\nLeast busy times by facility:\n")
for facility in summary["facility_name"].unique():
    print(f"\n=== {facility} ===")
    print(summary[summary["facility_name"] == facility].head(10).to_string(index=False))

for facility in analysis_df["facility_name"].unique():
    sub = analysis_df[analysis_df["facility_name"] == facility].copy()

    hourly = sub.groupby("hour")["percent_full"].mean().reindex(range(24))

    plt.figure(figsize=(10, 5))
    plt.plot(hourly.index, hourly.values, marker="o")
    plt.title(f"{facility} - Average Occupancy by Hour")
    plt.xlabel("Hour of Day")
    plt.ylabel("% Full")
    plt.xticks(range(24))
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{facility.replace(' ', '_')}_hourly.png", dpi=160)
    plt.close()

    pivot = sub.pivot_table(
        index="day",
        columns="hour",
        values="percent_full",
        aggfunc="mean"
    )

    pivot = pivot.reindex(index=day_order, columns=range(24))

    plt.figure(figsize=(12, 5))
    plt.imshow(pivot.values, aspect="auto")
    plt.colorbar(label="% Full")
    plt.title(f"{facility} - Weekly Heatmap")
    plt.xlabel("Hour")
    plt.ylabel("Day")
    plt.xticks(range(24), range(24))
    plt.yticks(range(len(pivot.index)), pivot.index)
    plt.tight_layout()
    plt.savefig(f"{facility.replace(' ', '_')}_heatmap.png", dpi=160)
    plt.close()

today_name = pd.Timestamp.now(tz="America/Los_Angeles").day_name()

lines = []
lines.append(f"Best gym times for {today_name}\n")

today_summary = summary[summary["day"] == today_name].copy()

if today_summary.empty:
    lines.append("No open-gym data is available for today yet.\n")
else:
    for facility in today_summary["facility_name"].unique():
        sub = today_summary[today_summary["facility_name"] == facility].sort_values("avg_percent")

        if sub.empty:
            continue

        best = sub.iloc[0]

        hour = int(best["hour"])
        percent = round(float(best["avg_percent"]), 1)
        hour_display = f"{hour % 12 or 12}:00 {'AM' if hour < 12 else 'PM'}"

        lines.append(f"{facility}:")
        lines.append(f"Best time today: {hour_display} (~{percent}% full)\n")

with open("best_time_today.txt", "w") as f:
    f.write("\n".join(lines))

print("\nSaved graphs, best_times_summary.csv, and best_time_today.txt")
