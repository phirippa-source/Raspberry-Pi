import csv
import math
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
        t_sec = float(row["t_ms"]) / 1000.0
        ax_val = float(row["ax"])
        ay_val = float(row["ay"])
        az_val = float(row["az"])
        gx_val = float(row["gx"])
        gy_val = float(row["gy"])
        gz_val = float(row["gz"])

        t.append(t_sec)
        ax.append(ax_val)
        ay.append(ay_val)
        az.append(az_val)
        gx.append(gx_val)
        gy.append(gy_val)
        gz.append(gz_val)

# magnitude 계산
a_mag = []
g_mag = []

for i in range(len(t)):
    a = math.sqrt(ax[i]**2 + ay[i]**2 + az[i]**2)
    g = math.sqrt(gx[i]**2 + gy[i]**2 + gz[i]**2)
    a_mag.append(a)
    g_mag.append(g)

fig, axes = plt.subplots(8, 1, figsize=(12, 12), sharex=True)

axes[0].plot(t, ax)
axes[0].set_ylabel("ax [g]")
axes[0].grid(True)
axes[0].set_title("LSM6DS3 6-axis + magnitude")

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
axes[5].grid(True)

axes[6].plot(t, a_mag)
axes[6].set_ylabel("a_mag [g]")
axes[6].grid(True)

axes[7].plot(t, g_mag)
axes[7].set_ylabel("g_mag [dps]")
axes[7].set_xlabel("Time [s]")
axes[7].grid(True)

plt.tight_layout()
plt.show()
