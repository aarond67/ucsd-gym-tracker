import matplotlib
matplotlib.use("Agg")

import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("ucsd_occupancy_history.csv")

df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
df = df.dropna(subset=["timestamp", "percent_full", "facility_name"]).copy()

df["percent_full"] = pd.to_numeric(df["percent_full"], errors="coerce")
df = df.dropna(subset=["percent_full"]).copy()

df["hour"] = df["timestamp"].dt.hour
df["day"] = df["timestamp"].dt.day_name()

day_order = [
    "Monday", "Tuesday", "Wednesday",
    "Thursday", "Friday", "Saturday", "Sunday"
]

summary = (
    df.groupby(["facility_name", "day", "hour"])["percent_full"]
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

for facility in df["facility_name"].unique():
    sub = df[df["facility_name"] == facility].copy()

    hourly = sub.groupby("hour")["percent_full"].mean().sort_index()

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

    pivot = pivot.reindex(day_order)

    plt.figure(figsize=(12, 5))
    plt.imshow(pivot, aspect="auto")
    plt.colorbar(label="% Full")
    plt.title(f"{facility} - Weekly Heatmap")
    plt.xlabel("Hour")
    plt.ylabel("Day")
    plt.xticks(range(24))
    plt.yticks(range(len(pivot.index)), pivot.index)
    plt.tight_layout()
    plt.savefig(f"{facility.replace(' ', '_')}_heatmap.png", dpi=160)
    plt.close()

print("\nSaved graphs and best_times_summary.csv")

# ----------------------------
# 📅 BEST TIME TODAY
# ----------------------------

today_name = pd.Timestamp.now().day_name()

lines = []
lines.append(f"Best gym times for {today_name}\n")

for facility in df["facility_name"].unique():
    sub = summary[
        (summary["facility_name"] == facility) &
        (summary["day"] == today_name)
    ].sort_values("avg_percent")

    if sub.empty:
        continue

    best = sub.iloc[0]

    hour = int(best["hour"])
    percent = round(best["avg_percent"], 1)

    # convert to readable time
    hour_display = f"{hour % 12 or 12}:00 {'AM' if hour < 12 else 'PM'}"

    lines.append(f"{facility}:")
    lines.append(f"Best time today: {hour_display} (~{percent}% full)\n")

# save file
with open("best_time_today.txt", "w") as f:
    f.write("\n".join(lines))

print("\nSaved best_time_today.txt")
