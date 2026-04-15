import csv
import matplotlib.pyplot as plt

csv_file = "gesture_log.csv"

t = []
ax = []
ay = []
az = []
gx = []
gy = []
gz = []

with open(csv_file, "r", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        t.append(float(row["t_ms"]) / 1000.0)  # ms -> s
        ax.append(float(row["ax"]))
        ay.append(float(row["ay"]))
        az.append(float(row["az"]))
        gx.append(float(row["gx"]))
        gy.append(float(row["gy"]))
        gz.append(float(row["gz"]))

fig, axes = plt.subplots(6, 1, figsize=(12, 10), sharex=True)

axes[0].plot(t, ax)
axes[0].set_ylabel("ax [g]")
axes[0].grid(True)
axes[0].set_title("LSM6DS3 6-axis time series")

axes[1].plot(t, ay)
axes[1].set_ylabel("ay [g]")
axes[1].grid(True)

axes[2].plot(t, az)
axes[2].set_ylabel("az [g]")
axes[2].grid(True)

axes[3].plot(t, gx)
axes[3].set_ylabel("gx [dps]")
axes[3].grid(True)

axes[4].plot(t, gy)
axes[4].set_ylabel("gy [dps]")
axes[4].grid(True)

axes[5].plot(t, gz)
axes[5].set_ylabel("gz [dps]")
axes[5].set_xlabel("Time [s]")
axes[5].grid(True)

plt.tight_layout()
plt.show()
