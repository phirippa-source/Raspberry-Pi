import csv
import math
import matplotlib.pyplot as plt

csv_file = "gesture_log.csv"

# -----------------------------
# 사용자가 조절할 값
# -----------------------------
A_THRESHOLD = 0.08   # a_dyn = |a_mag - 1.0| 기준
G_THRESHOLD = 20.0   # g_mag 기준 [dps]

# 너무 짧은 잡음 구간 제거용
MIN_ACTIVE_SAMPLES = 5   # threshold 초과가 최소 몇 샘플 연속이어야 동작으로 볼지
MIN_IDLE_SAMPLES = 8     # threshold 미만이 몇 샘플 연속이어야 동작 종료로 볼지

# -----------------------------
# CSV 읽기
# -----------------------------
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

# -----------------------------
# magnitude 계산
# -----------------------------
a_mag = []
a_dyn = []
g_mag = []

for i in range(len(t)):
    am = math.sqrt(ax[i]**2 + ay[i]**2 + az[i]**2)
    gm = math.sqrt(gx[i]**2 + gy[i]**2 + gz[i]**2)

    a_mag.append(am)
    a_dyn.append(abs(am - 1.0))   # 중력 1g 기준에서 얼마나 벗어났는지
    g_mag.append(gm)

# -----------------------------
# 동작 여부 판단
# motion[i] = True 이면 동작 후보
# -----------------------------
motion_raw = []
for i in range(len(t)):
    is_active = (a_dyn[i] > A_THRESHOLD) or (g_mag[i] > G_THRESHOLD)
    motion_raw.append(is_active)

# -----------------------------
# 짧은 잡음 구간 제거 + 동작 구간 정리
# -----------------------------
motion = [False] * len(t)

i = 0
n = len(t)

while i < n:
    if motion_raw[i]:
        start = i
        while i < n and motion_raw[i]:
            i += 1
        end = i  # end는 미포함

        if (end - start) >= MIN_ACTIVE_SAMPLES:
            for k in range(start, end):
                motion[k] = True
    else:
        i += 1

# 가까운 구간 사이의 짧은 idle은 메우기
i = 0
while i < n:
    if not motion[i]:
        start = i
        while i < n and not motion[i]:
            i += 1
        end = i

        # 앞뒤가 모두 active이고, idle 길이가 짧으면 이어붙임
        if start > 0 and end < n:
            if motion[start - 1] and motion[end] and (end - start) < MIN_IDLE_SAMPLES:
                for k in range(start, end):
                    motion[k] = True
    else:
        i += 1

# -----------------------------
# active 구간을 (start_idx, end_idx) 목록으로 추출
# -----------------------------
segments = []
i = 0
while i < n:
    if motion[i]:
        start = i
        while i < n and motion[i]:
            i += 1
        end = i - 1
        segments.append((start, end))
    else:
        i += 1

print("검출된 동작 구간 수 =", len(segments))
for idx, (s, e) in enumerate(segments, start=1):
    print(f"{idx}: {t[s]:.3f}s ~ {t[e]:.3f}s")

# -----------------------------
# 그래프
# -----------------------------
fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True)

# 1) a_mag
axes[0].plot(t, a_mag, label="a_mag")
axes[0].set_ylabel("a_mag [g]")
axes[0].set_title("Acceleration / Gyroscope magnitude with thresholds")
axes[0].grid(True)
axes[0].legend()

# 2) a_dyn + threshold
axes[1].plot(t, a_dyn, label="a_dyn = |a_mag - 1.0|")
axes[1].axhline(A_THRESHOLD, linestyle="--", label=f"A_THRESHOLD = {A_THRESHOLD}")
axes[1].set_ylabel("a_dyn [g]")
axes[1].grid(True)
axes[1].legend()

# 3) g_mag + threshold
axes[2].plot(t, g_mag, label="g_mag")
axes[2].axhline(G_THRESHOLD, linestyle="--", label=f"G_THRESHOLD = {G_THRESHOLD}")
axes[2].set_ylabel("g_mag [dps]")
axes[2].set_xlabel("Time [s]")
axes[2].grid(True)
axes[2].legend()

# 검출된 동작 구간 색칠
for s, e in segments:
    t0 = t[s]
    t1 = t[e]
    for ax_plot in axes:
        ax_plot.axvspan(t0, t1, alpha=0.2)

plt.tight_layout()
plt.show()
