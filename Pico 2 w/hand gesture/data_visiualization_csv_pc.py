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
        t.append(float(row["t_ms"]) / 1000.0)  # 초 단위로 변환
        ax.append(float(row["ax"]))
        ay.append(float(row["ay"]))
        az.append(float(row["az"]))
        gx.append(float(row["gx"]))
        gy.append(float(row["gy"]))
        gz.append(float(row["gz"]))

plt.figure(figsize=(12, 8))

plt.subplot(2, 1, 1)
plt.plot(t, ax, label="ax")
plt.plot(t, ay, label="ay")
plt.plot(t, az, label="az")
plt.title("Acceleration")
plt.xlabel("Time [s]")
plt.ylabel("g")
plt.grid(True)
plt.legend()

plt.subplot(2, 1, 2)
plt.plot(t, gx, label="gx")
plt.plot(t, gy, label="gy")
plt.plot(t, gz, label="gz")
plt.title("Gyroscope")
plt.xlabel("Time [s]")
plt.ylabel("dps")
plt.grid(True)
plt.legend()

plt.tight_layout()
plt.show()
