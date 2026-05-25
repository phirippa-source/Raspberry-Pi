import csv
import math
import os
import stat
import time
import shutil
from pathlib import Path

import matplotlib.pyplot as plt

# =========================================================
# 사용자 설정
# =========================================================
BASE_DIR = Path("./dataset")

CLASS_DIRS = {
    "right": BASE_DIR / "right",
    "left": BASE_DIR / "left",
    "forward": BASE_DIR / "forward",
    "stop": BASE_DIR / "stop",
}

PROCESSED_DIR = BASE_DIR / "processed"
OUTPUT_LONG_CSV = PROCESSED_DIR / "gestures_long.csv"
OUTPUT_WIDE_CSV = PROCESSED_DIR / "gestures_wide.csv"
OUTPUT_SEGMENT_DIR = PROCESSED_DIR / "samples"

# 최종 샘플 길이
TARGET_LEN = 84   # 필요하면 90으로 변경

# threshold
A_THRESHOLD = 0.08
G_THRESHOLD = 22.0

# 너무 짧은 active 제거 / 너무 짧은 idle 메우기
MIN_ACTIVE_SAMPLES = 10
MIN_IDLE_SAMPLES = 15

# 구간 앞뒤 여유
PAD_BEFORE = 5
PAD_AFTER = 5

# 옵션
SHOW_PLOT = False          # True면 raw 파일마다 그래프 표시
SAVE_SEGMENT_FILES = True  # 개별 샘플 csv 저장 여부
FLOAT_FMT = "{:.6f}"


# =========================================================
# 파일/폴더 삭제 보조 함수 (Windows 대응)
# =========================================================
def _on_rm_error(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def force_remove_file(path: Path, retries=5, delay=0.3):
    for attempt in range(retries):
        try:
            if path.exists():
                os.chmod(path, stat.S_IWRITE)
                path.unlink()
            return
        except PermissionError:
            if attempt == retries - 1:
                raise
            time.sleep(delay)


def force_remove_tree_contents(folder: Path, retries=5, delay=0.3):
    if not folder.exists():
        return

    for item in folder.iterdir():
        for attempt in range(retries):
            try:
                if item.is_file() or item.is_symlink():
                    os.chmod(item, stat.S_IWRITE)
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item, onerror=_on_rm_error)
                break
            except PermissionError:
                if attempt == retries - 1:
                    raise
                time.sleep(delay)


# =========================================================
# processed 폴더 정리
# - long/wide는 삭제
# - samples 폴더는 남겨두고 내부만 비움
# =========================================================
def clean_processed_dir():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_SEGMENT_DIR.mkdir(parents=True, exist_ok=True)

    if OUTPUT_LONG_CSV.exists():
        force_remove_file(OUTPUT_LONG_CSV)

    if OUTPUT_WIDE_CSV.exists():
        force_remove_file(OUTPUT_WIDE_CSV)

    force_remove_tree_contents(OUTPUT_SEGMENT_DIR)


# =========================================================
# raw CSV 자동 수집
# =========================================================
def discover_jobs():
    jobs = []

    for label, folder in CLASS_DIRS.items():
        if not folder.exists():
            print(f"[주의] 폴더가 없습니다: {folder}")
            continue

        # 각 클래스 폴더 안의 모든 csv를 처리
        files = sorted(folder.glob("*.csv"))

        for file_path in files:
            jobs.append((file_path, label))

    return jobs


# =========================================================
# CSV 읽기
# =========================================================
def load_csv(filename: Path):
    t = []
    ax = []
    ay = []
    az = []
    gx = []
    gy = []
    gz = []

    with filename.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            t.append(float(row["t_ms"]))   # ms
            ax.append(float(row["ax"]))
            ay.append(float(row["ay"]))
            az.append(float(row["az"]))
            gx.append(float(row["gx"]))
            gy.append(float(row["gy"]))
            gz.append(float(row["gz"]))

    return t, ax, ay, az, gx, gy, gz


# =========================================================
# 특징 계산
# =========================================================
def compute_features(ax, ay, az, gx, gy, gz):
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


# =========================================================
# 1차 motion 판정
# =========================================================
def detect_motion_raw(a_dyn, g_mag, a_threshold, g_threshold):
    motion_raw = []

    for i in range(len(a_dyn)):
        active = (a_dyn[i] > a_threshold) or (g_mag[i] > g_threshold)
        motion_raw.append(active)

    return motion_raw


# =========================================================
# 너무 짧은 active 제거
# =========================================================
def remove_short_active_runs(motion_raw, min_active_samples):
    n = len(motion_raw)
    motion = [False] * n

    i = 0
    while i < n:
        if motion_raw[i]:
            start = i
            while i < n and motion_raw[i]:
                i += 1
            end = i  # 미포함

            if (end - start) >= min_active_samples:
                for k in range(start, end):
                    motion[k] = True
        else:
            i += 1

    return motion


# =========================================================
# 너무 짧은 idle 구간 메우기
# =========================================================
def fill_short_idle_runs(motion, min_idle_samples):
    n = len(motion)
    out = motion[:]

    i = 0
    while i < n:
        if not out[i]:
            start = i
            while i < n and not out[i]:
                i += 1
            end = i  # 미포함

            if start > 0 and end < n:
                if out[start - 1] and out[end] and (end - start) < min_idle_samples:
                    for k in range(start, end):
                        out[k] = True
        else:
            i += 1

    return out


# =========================================================
# True 구간 추출
# =========================================================
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


# =========================================================
# 앞뒤 padding 추가
# =========================================================
def pad_segments(segments, total_len, pad_before, pad_after):
    out = []

    for s, e in segments:
        ps = max(0, s - pad_before)
        pe = min(total_len - 1, e + pad_after)
        out.append((ps, pe))

    return out


# =========================================================
# 리샘플링
# =========================================================
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
            v = seq[left] * (1.0 - alpha) + seq[right] * alpha
            out.append(v)

    return out


# =========================================================
# 하나의 구간 -> TARGET_LEN x 6 샘플
# =========================================================
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
        sample.append([
            rs_ax[i], rs_ay[i], rs_az[i],
            rs_gx[i], rs_gy[i], rs_gz[i]
        ])

    return sample


# =========================================================
# 헤더
# =========================================================
def long_header():
    return ["sample_id", "label", "time_idx", "ax", "ay", "az", "gx", "gy", "gz"]


def wide_header(target_len):
    header = ["sample_id", "label"]
    for i in range(target_len):
        header.extend([
            f"ax_{i}", f"ay_{i}", f"az_{i}",
            f"gx_{i}", f"gy_{i}", f"gz_{i}"
        ])
    return header


# =========================================================
# long CSV 저장
# =========================================================
def save_long_csv(filename, samples, labels, sample_ids):
    filename.parent.mkdir(parents=True, exist_ok=True)

    with filename.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(long_header())

        for sample, label, sample_id in zip(samples, labels, sample_ids):
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


# =========================================================
# wide CSV 저장
# =========================================================
def save_wide_csv(filename, samples, labels, sample_ids, target_len):
    filename.parent.mkdir(parents=True, exist_ok=True)

    with filename.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(wide_header(target_len))

        for sample, label, sample_id in zip(samples, labels, sample_ids):
            row = [sample_id, label]
            for time_step in sample:
                for v in time_step:
                    row.append(FLOAT_FMT.format(v))
            writer.writerow(row)


# =========================================================
# 개별 샘플 CSV 저장
# =========================================================
def save_segment_files(samples, label, source_csv, sample_ids, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)

    base = source_csv.stem

    for local_idx, (sample, sample_id) in enumerate(zip(samples, sample_ids), start=1):
        filename = output_dir / f"{base}_seg_{local_idx:03d}_id_{sample_id:03d}_{label}.csv"

        with filename.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["time_idx", "ax", "ay", "az", "gx", "gy", "gz"])

            for time_idx, row in enumerate(sample):
                writer.writerow([
                    time_idx,
                    FLOAT_FMT.format(row[0]),
                    FLOAT_FMT.format(row[1]),
                    FLOAT_FMT.format(row[2]),
                    FLOAT_FMT.format(row[3]),
                    FLOAT_FMT.format(row[4]),
                    FLOAT_FMT.format(row[5]),
                ])


# =========================================================
# 그래프 표시
# =========================================================
def show_plot(t, a_mag, a_dyn, g_mag, segments, a_threshold, g_threshold, title):
    plt.close("all")

    t_sec = [x / 1000.0 for x in t]

    fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True)

    axes[0].plot(t_sec, a_mag, label="a_mag")
    axes[0].set_ylabel("a_mag [g]")
    axes[0].set_title(title)
    axes[0].grid(True)
    axes[0].legend()

    axes[1].plot(t_sec, a_dyn, label="a_dyn = |a_mag - 1.0|")
    axes[1].axhline(a_threshold, linestyle="--", label=f"A_THRESHOLD = {a_threshold}")
    axes[1].set_ylabel("a_dyn [g]")
    axes[1].grid(True)
    axes[1].legend()

    axes[2].plot(t_sec, g_mag, label="g_mag")
    axes[2].axhline(g_threshold, linestyle="--", label=f"G_THRESHOLD = {g_threshold}")
    axes[2].set_ylabel("g_mag [dps]")
    axes[2].set_xlabel("Time [s]")
    axes[2].grid(True)
    axes[2].legend()

    for s, e in segments:
        t0 = t_sec[s]
        t1 = t_sec[e]
        for ax_plot in axes:
            ax_plot.axvspan(t0, t1, alpha=0.2)

    plt.tight_layout()
    plt.show(block=True)


# =========================================================
# 메인
# =========================================================
def main():
    print("processed 폴더 정리 중...")
    clean_processed_dir()

    jobs = discover_jobs()

    if len(jobs) == 0:
        print("처리할 raw CSV 파일이 없습니다.")
        return

    print(f"발견된 raw CSV 파일 수 = {len(jobs)}")

    all_samples = []
    all_labels = []
    all_sample_ids = []

    next_sample_id = 1

    for input_csv, label in jobs:
        print()
        print("=" * 70)
        print("INPUT_CSV =", input_csv)
        print("LABEL     =", label)

        t, ax, ay, az, gx, gy, gz = load_csv(input_csv)

        if len(t) == 0:
            print("CSV 파일이 비어 있습니다. 건너뜁니다.")
            continue

        a_mag, a_dyn, g_mag = compute_features(ax, ay, az, gx, gy, gz)

        motion_raw = detect_motion_raw(a_dyn, g_mag, A_THRESHOLD, G_THRESHOLD)
        motion = remove_short_active_runs(motion_raw, MIN_ACTIVE_SAMPLES)
        motion = fill_short_idle_runs(motion, MIN_IDLE_SAMPLES)

        segments = extract_segments(motion)
        segments = pad_segments(segments, len(t), PAD_BEFORE, PAD_AFTER)

        print("검출된 동작 구간 수 =", len(segments))
        for idx, (s, e) in enumerate(segments, start=1):
            print(f"{idx}: idx {s} ~ {e}, {t[s]/1000.0:.3f}s ~ {t[e]/1000.0:.3f}s")

        if len(segments) == 0:
            print("이 파일에서는 저장할 샘플이 없습니다.")
            print("threshold 값을 조정해보세요.")
            continue

        if SHOW_PLOT:
            show_plot(
                t, a_mag, a_dyn, g_mag, segments,
                A_THRESHOLD, G_THRESHOLD,
                title=f"{input_csv.name}  /  label={label}"
            )

        current_samples = []
        current_labels = []
        current_ids = []

        for s, e in segments:
            sample = make_resampled_sample(
                ax, ay, az, gx, gy, gz,
                s, e, TARGET_LEN
            )
            current_samples.append(sample)
            current_labels.append(label)
            current_ids.append(next_sample_id)
            next_sample_id += 1

        if SAVE_SEGMENT_FILES:
            save_segment_files(
                current_samples,
                label=label,
                source_csv=input_csv,
                sample_ids=current_ids,
                output_dir=OUTPUT_SEGMENT_DIR
            )

        all_samples.extend(current_samples)
        all_labels.extend(current_labels)
        all_sample_ids.extend(current_ids)

    if len(all_samples) == 0:
        print()
        print("최종적으로 저장할 샘플이 없습니다.")
        return

    save_long_csv(
        OUTPUT_LONG_CSV,
        all_samples,
        all_labels,
        all_sample_ids
    )

    save_wide_csv(
        OUTPUT_WIDE_CSV,
        all_samples,
        all_labels,
        all_sample_ids,
        TARGET_LEN
    )

    print()
    print("=" * 70)
    print("최종 저장 완료")
    print(" - long  :", OUTPUT_LONG_CSV)
    print(" - wide  :", OUTPUT_WIDE_CSV)
    if SAVE_SEGMENT_FILES:
        print(" - files :", OUTPUT_SEGMENT_DIR)
    print("총 샘플 수 =", len(all_samples))
    print("샘플 shape = {} x 6".format(TARGET_LEN))
    print("wide 입력 차원 =", TARGET_LEN * 6)

    class_count = {}
    for label in all_labels:
        class_count[label] = class_count.get(label, 0) + 1

    print("클래스별 샘플 수:")
    for key in sorted(class_count.keys()):
        print(f" - {key}: {class_count[key]}")


if __name__ == "__main__":
    main()
