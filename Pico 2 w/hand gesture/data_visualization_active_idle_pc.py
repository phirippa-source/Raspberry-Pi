import csv
import math
import matplotlib.pyplot as plt

# =========================================
# 사용자 설정
# =========================================
INPUT_CSV = "./dataset/right/sample_right_01.csv"   # 분석할 raw CSV 파일
A_THRESHOLD = 0.08          # a_dyn 기준
G_THRESHOLD = 22.0          # g_mag 기준 [dps]

MIN_ACTIVE_SAMPLES = 10      # 너무 짧은 active 구간 제거
MIN_IDLE_SAMPLES = 15        # 너무 짧은 idle 구간 메우기
PAD_BEFORE = 5              # 시작 전 여유
PAD_AFTER = 5               # 끝난 후 여유

SHOW_PLOT = True            # 그래프 표시 여부


# =========================================
# CSV 읽기
# =========================================
def load_csv(filename):
    t = []
    ax = []
    ay = []
    az = []
    gx = []
    gy = []
    gz = []

    with open(filename, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            t.append(float(row["t_ms"]))
            ax.append(float(row["ax"]))
            ay.append(float(row["ay"]))
            az.append(float(row["az"]))
            gx.append(float(row["gx"]))
            gy.append(float(row["gy"]))
            gz.append(float(row["gz"]))

    return t, ax, ay, az, gx, gy, gz


# =========================================
# 특징 계산
# =========================================
def compute_features(ax, ay, az, gx, gy, gz):
    a_mag = []
    a_dyn = []
    g_mag = []

    for i in range(len(ax)):
        am = math.sqrt(ax[i]**2 + ay[i]**2 + az[i]**2)
        gm = math.sqrt(gx[i]**2 + gy[i]**2 + gz[i]**2)

        a_mag.append(am)
        a_dyn.append(abs(am - 1.0))   # 정지 시 1g 근처이므로 1과의 차이를 사용
        g_mag.append(gm)

    return a_mag, a_dyn, g_mag


# =========================================
# 1차 motion 판정
# =========================================
def detect_motion_raw(a_dyn, g_mag, a_threshold, g_threshold):
    motion_raw = []

    for i in range(len(a_dyn)):
        active = (a_dyn[i] > a_threshold) or (g_mag[i] > g_threshold)
        motion_raw.append(active)

    return motion_raw


# =========================================
# 너무 짧은 active 구간 제거
# =========================================
def remove_short_active_runs(motion_raw, min_active_samples):
    n = len(motion_raw)
    motion = [False] * n

    i = 0
    while i < n:
        if motion_raw[i]:
            start = i
            while i < n and motion_raw[i]:
                i += 1
            end = i  # end는 미포함

            if (end - start) >= min_active_samples:
                for k in range(start, end):
                    motion[k] = True
        else:
            i += 1

    return motion


# =========================================
# 너무 짧은 idle 구간 메우기
# =========================================
def fill_short_idle_runs(motion, min_idle_samples):
    n = len(motion)
    out = motion[:]

    i = 0
    while i < n:
        if not out[i]:
            start = i
            while i < n and not out[i]:
                i += 1
            end = i  # end는 미포함

            # 앞뒤가 모두 active이고 idle 길이가 짧으면 같은 동작으로 연결
            if start > 0 and end < n:
                if out[start - 1] and out[end] and (end - start) < min_idle_samples:
                    for k in range(start, end):
                        out[k] = True
        else:
            i += 1

    return out


# =========================================
# True 구간을 start~end 목록으로 추출
# end는 포함
# =========================================
def extract_segments(motion):
    segments = []
    n = len(motion)

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

    return segments


# =========================================
# 앞뒤 padding 추가
# =========================================
def pad_segments(segments, total_len, pad_before, pad_after):
    padded = []

    for s, e in segments:
        ps = max(0, s - pad_before)
        pe = min(total_len - 1, e + pad_after)
        padded.append((ps, pe))

    return padded


# =========================================
# 그래프 표시
# =========================================
def show_plot(t, a_dyn, g_mag, segments, a_threshold, g_threshold):
    t_sec = [x / 1000.0 for x in t]

    plt.close("all")
    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True)

    axes[0].plot(t_sec, a_dyn, label="a_dyn = |a_mag - 1.0|")
    axes[0].axhline(a_threshold, linestyle="--", label=f"A_THRESHOLD = {a_threshold}")
    axes[0].set_ylabel("a_dyn [g]")
    axes[0].grid(True)
    axes[0].legend()

    axes[1].plot(t_sec, g_mag, label="g_mag")
    axes[1].axhline(g_threshold, linestyle="--", label=f"G_THRESHOLD = {g_threshold}")
    axes[1].set_ylabel("g_mag [dps]")
    axes[1].set_xlabel("Time [s]")
    axes[1].grid(True)
    axes[1].legend()

    # 검출된 동작 구간 색칠
    for s, e in segments:
        t0 = t_sec[s]
        t1 = t_sec[e]
        axes[0].axvspan(t0, t1, alpha=0.2)
        axes[1].axvspan(t0, t1, alpha=0.2)

    plt.tight_layout()
    plt.show(block=True)


# =========================================
# 메인
# =========================================
def main():
    t, ax, ay, az, gx, gy, gz = load_csv(INPUT_CSV)

    if len(t) == 0:
        print("CSV 파일이 비어 있습니다.")
        return

    a_mag, a_dyn, g_mag = compute_features(ax, ay, az, gx, gy, gz)

    motion_raw = detect_motion_raw(a_dyn, g_mag, A_THRESHOLD, G_THRESHOLD)
    motion = remove_short_active_runs(motion_raw, MIN_ACTIVE_SAMPLES)
    motion = fill_short_idle_runs(motion, MIN_IDLE_SAMPLES)

    segments = extract_segments(motion)
    segments = pad_segments(segments, len(t), PAD_BEFORE, PAD_AFTER)

    print("검출된 동작 구간 수 =", len(segments))
    for idx, (s, e) in enumerate(segments, start=1):
        print(f"{idx}: idx {s} ~ {e},  {t[s]/1000.0:.3f}s ~ {t[e]/1000.0:.3f}s")

    if SHOW_PLOT:
        show_plot(t, a_dyn, g_mag, segments, A_THRESHOLD, G_THRESHOLD)


if __name__ == "__main__":
    main()
