import csv
import math
import os
import matplotlib.pyplot as plt

# =========================================================
# 사용자 설정
# =========================================================
INPUT_CSV = "gesture_log.csv"
OUTPUT_LONG_CSV = "gestures_long.csv"
OUTPUT_WIDE_CSV = "gestures_wide.csv"

LABEL = "left"
TARGET_LEN = 84

A_THRESHOLD = 0.08
G_THRESHOLD = 22.0

MIN_ACTIVE_SAMPLES = 5
MIN_IDLE_SAMPLES = 8

PAD_BEFORE = 5
PAD_AFTER = 5

FLOAT_FMT = "{:.6f}"
APPEND_MODE = False


def load_gesture_csv(filename):
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


def compute_magnitudes(ax, ay, az, gx, gy, gz):
    a_mag = []
    a_dyn = []
    g_mag = []

    for i in range(len(ax)):
        am = math.sqrt(ax[i] ** 2 + ay[i] ** 2 + az[i] ** 2)
        gm = math.sqrt(gx[i] ** 2 + gy[i] ** 2 + gz[i] ** 2)
        a_mag.append(am)
        a_dyn.append(abs(am - 1.0))
        g_mag.append(gm)

    return a_mag, a_dyn, g_mag


def detect_motion_raw(a_dyn, g_mag, a_threshold, g_threshold):
    motion_raw = []
    for i in range(len(a_dyn)):
        active = (a_dyn[i] > a_threshold) or (g_mag[i] > g_threshold)
        motion_raw.append(active)
    return motion_raw


def remove_short_active_runs(motion_raw, min_active_samples):
    n = len(motion_raw)
    motion = [False] * n

    i = 0
    while i < n:
        if motion_raw[i]:
            start = i
            while i < n and motion_raw[i]:
                i += 1
            end = i
            if (end - start) >= min_active_samples:
                for k in range(start, end):
                    motion[k] = True
        else:
            i += 1

    return motion


def fill_short_idle_runs(motion, min_idle_samples):
    n = len(motion)
    out = motion[:]

    i = 0
    while i < n:
        if not out[i]:
            start = i
            while i < n and not out[i]:
                i += 1
            end = i

            if start > 0 and end < n:
                if out[start - 1] and out[end] and (end - start) < min_idle_samples:
                    for k in range(start, end):
                        out[k] = True
        else:
            i += 1

    return out


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


def pad_segments(segments, total_len, pad_before, pad_after):
    padded = []
    for s, e in segments:
        ps = max(0, s - pad_before)
        pe = min(total_len - 1, e + pad_after)
        padded.append((ps, pe))
    return padded


def resample_1d(seq, target_len):
    src_len = len(seq)

    if src_len == 0:
        return [0.0] * target_len

    if src_len == 1:
        return [seq[0]] * target_len

    out = []
    for i in range(target_len):
        pos = i * (src_len - 1) / (target_len - 1)
        left = int(math.floor(pos))
        right = int(math.ceil(pos))

        if left == right:
            out.append(seq[left])
        else:
            alpha = pos - left
            val = seq[left] * (1.0 - alpha) + seq[right] * alpha
            out.append(val)

    return out


def make_resampled_sample(ax, ay, az, gx, gy, gz, start_idx, end_idx, target_len):
    seg_ax = ax[start_idx:end_idx + 1]
    seg_ay = ay[start_idx:end_idx + 1]
    seg_az = az[start_idx:end_idx + 1]
    seg_gx = gx[start_idx:end_idx + 1]
    seg_gy = gy[start_idx:end_idx + 1]
    seg_gz = gz[start_idx:end_idx + 1]

    rs_ax = resample_1d(seg_ax, target_len)
    rs_ay = resample_1d(seg_ay, target_len)
    rs_az = resample_1d(seg_az, target_len)
    rs_gx = resample_1d(seg_gx, target_len)
    rs_gy = resample_1d(seg_gy, target_len)
    rs_gz = resample_1d(seg_gz, target_len)

    sample = []
    for i in range(target_len):
        sample.append([rs_ax[i], rs_ay[i], rs_az[i], rs_gx[i], rs_gy[i], rs_gz[i]])

    return sample


def long_header():
    return ["sample_id", "label", "time_idx", "ax", "ay", "az", "gx", "gy", "gz"]


def wide_header(target_len):
    header = ["sample_id", "label"]
    for i in range(target_len):
        header.extend([f"ax_{i}", f"ay_{i}", f"az_{i}", f"gx_{i}", f"gy_{i}", f"gz_{i}"])
    return header


def get_last_sample_id(filename):
    if not os.path.exists(filename):
        return 0

    last_id = 0
    with open(filename, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = int(row["sample_id"])
            if sid > last_id:
                last_id = sid
    return last_id


def save_long_csv(filename, samples, labels, start_sample_id=1, append=False):
    mode = "a" if append else "w"
    need_header = (not append) or (append and not os.path.exists(filename))

    with open(filename, mode, newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if need_header:
            writer.writerow(long_header())

        sample_id = start_sample_id
        for sample, label in zip(samples, labels):
            for time_idx, row in enumerate(sample):
                writer.writerow([
                    sample_id,
                    label,
                    time_idx,
                    FLOAT_FMT.format(row[0]),
                    FLOAT_FMT.format(row[1]),
                    FLOAT_FMT.format(row[2]),
                    FLOAT_FMT.format(row[3]),
                    FLOAT_FMT.format(row[4]),
                    FLOAT_FMT.format(row[5]),
                ])
            sample_id += 1


def save_wide_csv(filename, samples, labels, target_len, start_sample_id=1, append=False):
    mode = "a" if append else "w"
    need_header = (not append) or (append and not os.path.exists(filename))

    with open(filename, mode, newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if need_header:
            writer.writerow(wide_header(target_len))

        sample_id = start_sample_id
        for sample, label in zip(samples, labels):
            row = [sample_id, label]
            for time_step in sample:
                for v in time_step:
                    row.append(FLOAT_FMT.format(v))
            writer.writerow(row)
            sample_id += 1


def show_detection_plot(t, a_dyn, g_mag, segments):
    plt.close("all")

    t_sec = [x / 1000.0 for x in t]

    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True)

    axes[0].plot(t_sec, a_dyn, label="a_dyn = |a_mag - 1.0|")
    axes[0].axhline(A_THRESHOLD, linestyle="--", label=f"A_THRESHOLD = {A_THRESHOLD}")
    axes[0].set_ylabel("a_dyn [g]")
    axes[0].grid(True)
    axes[0].legend()

    axes[1].plot(t_sec, g_mag, label="g_mag")
    axes[1].axhline(G_THRESHOLD, linestyle="--", label=f"G_THRESHOLD = {G_THRESHOLD}")
    axes[1].set_ylabel("g_mag [dps]")
    axes[1].set_xlabel("Time [s]")
    axes[1].grid(True)
    axes[1].legend()

    for s, e in segments:
        t0 = t_sec[s]
        t1 = t_sec[e]
        axes[0].axvspan(t0, t1, alpha=0.2)
        axes[1].axvspan(t0, t1, alpha=0.2)

    plt.tight_layout()
    plt.show(block=True)


def main():
    t, ax, ay, az, gx, gy, gz = load_gesture_csv(INPUT_CSV)
    n = len(t)

    if n == 0:
        print("입력 CSV가 비어 있습니다.")
        return

    a_mag, a_dyn, g_mag = compute_magnitudes(ax, ay, az, gx, gy, gz)

    motion_raw = detect_motion_raw(a_dyn, g_mag, A_THRESHOLD, G_THRESHOLD)
    motion = remove_short_active_runs(motion_raw, MIN_ACTIVE_SAMPLES)
    motion = fill_short_idle_runs(motion, MIN_IDLE_SAMPLES)

    segments = extract_segments(motion)
    segments = pad_segments(segments, n, PAD_BEFORE, PAD_AFTER)

    print("검출된 동작 구간 수 =", len(segments))
    for i, (s, e) in enumerate(segments, start=1):
        print(f"{i}: idx {s} ~ {e}, t={t[s]/1000.0:.3f}s ~ {t[e]/1000.0:.3f}s")

    if len(segments) == 0:
        print("동작 구간이 검출되지 않았습니다.")
        print("A_THRESHOLD / G_THRESHOLD 값을 조정해보세요.")
        return

    show_detection_plot(t, a_dyn, g_mag, segments)

    samples = []
    labels = []

    for s, e in segments:
        sample = make_resampled_sample(ax, ay, az, gx, gy, gz, s, e, TARGET_LEN)
        samples.append(sample)
        labels.append(LABEL)

    if APPEND_MODE:
        last_id_long = get_last_sample_id(OUTPUT_LONG_CSV)
        last_id_wide = get_last_sample_id(OUTPUT_WIDE_CSV)
        start_sample_id = max(last_id_long, last_id_wide) + 1
    else:
        start_sample_id = 1

    save_long_csv(
        OUTPUT_LONG_CSV,
        samples,
        labels,
        start_sample_id=start_sample_id,
        append=APPEND_MODE,
    )

    save_wide_csv(
        OUTPUT_WIDE_CSV,
        samples,
        labels,
        target_len=TARGET_LEN,
        start_sample_id=start_sample_id,
        append=APPEND_MODE,
    )

    print()
    print("저장 완료")
    print(" -", OUTPUT_LONG_CSV)
    print(" -", OUTPUT_WIDE_CSV)
    print("샘플 개수 =", len(samples))
    print("샘플 shape = {} x 6".format(TARGET_LEN))
    print("wide 입력 차원 =", TARGET_LEN * 6)


if __name__ == "__main__":
    main()
