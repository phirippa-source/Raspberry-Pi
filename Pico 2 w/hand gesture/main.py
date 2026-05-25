from machine import Pin, I2C
import time
import math

from lsm6ds3_simple import LSM6DS3
from pico_knn import predict_debug
from knn_model_data import FEATURE_COUNT


# =========================================================
# 사용자 설정
# =========================================================

# I2C 설정
I2C_ID = 0
SDA_PIN = 0
SCL_PIN = 1
I2C_FREQ = 400000

# LSM6DS3 주소
# 보드에 따라 0x6B 또는 0x6A일 수 있음
IMU_ADDR = 0x6B

# 학습 때 사용한 전처리 설정과 맞추는 값
TARGET_LEN = 84

A_THRESHOLD = 0.08
G_THRESHOLD = 22.0

MIN_ACTIVE_SAMPLES = 10
MIN_IDLE_SAMPLES = 15

PAD_BEFORE = 5
PAD_AFTER = 5

# 센서 읽기 주기
# 학습용 raw CSV를 수집할 때와 비슷하게 맞추는 것이 좋음
SAMPLE_INTERVAL_MS = 10

# 너무 긴 동작 구간 방지
MAX_SEGMENT_SAMPLES = 300

# 예측 후 다음 동작을 받기 전 잠깐 대기
COOLDOWN_MS = 700


# =========================================================
# LED
# =========================================================
led = Pin("LED", Pin.OUT)


# =========================================================
# 특징 계산
# =========================================================
def calc_a_dyn_g_mag(sample):
    ax, ay, az, gx, gy, gz = sample

    a_mag = math.sqrt(ax * ax + ay * ay + az * az)
    a_dyn = abs(a_mag - 1.0)

    g_mag = math.sqrt(gx * gx + gy * gy + gz * gz)

    return a_dyn, g_mag


def is_active(sample):
    a_dyn, g_mag = calc_a_dyn_g_mag(sample)
    return (a_dyn > A_THRESHOLD) or (g_mag > G_THRESHOLD)


# =========================================================
# 1차원 리샘플링
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
        left = int(pos)
        right = left + 1

        if right >= src_len:
            out.append(seq[left])
        else:
            alpha = pos - left
            v = seq[left] * (1.0 - alpha) + seq[right] * alpha
            out.append(v)

    return out


# =========================================================
# segment_samples -> 84 x 6 리샘플링
# =========================================================
def resample_segment(segment_samples, target_len):
    ax = [s[0] for s in segment_samples]
    ay = [s[1] for s in segment_samples]
    az = [s[2] for s in segment_samples]
    gx = [s[3] for s in segment_samples]
    gy = [s[4] for s in segment_samples]
    gz = [s[5] for s in segment_samples]

    rs_ax = resample_1d(ax, target_len)
    rs_ay = resample_1d(ay, target_len)
    rs_az = resample_1d(az, target_len)
    rs_gx = resample_1d(gx, target_len)
    rs_gy = resample_1d(gy, target_len)
    rs_gz = resample_1d(gz, target_len)

    sample = []

    for i in range(target_len):
        sample.append((
            rs_ax[i],
            rs_ay[i],
            rs_az[i],
            rs_gx[i],
            rs_gy[i],
            rs_gz[i],
        ))

    return sample


# =========================================================
# 84 x 6 -> 504개 1차원 벡터
# 순서는 학습용 gestures_wide.csv와 반드시 같아야 함
# ax_0, ay_0, az_0, gx_0, gy_0, gz_0, ax_1, ...
# =========================================================
def flatten_sample(sample_84x6):
    raw_x = []

    for row in sample_84x6:
        ax, ay, az, gx, gy, gz = row
        raw_x.append(ax)
        raw_x.append(ay)
        raw_x.append(az)
        raw_x.append(gx)
        raw_x.append(gy)
        raw_x.append(gz)

    return raw_x


# =========================================================
# 실시간 동작 구간 하나 수집
# =========================================================
def collect_one_gesture(imu):
    print()
    print("동작 대기 중...")

    history = []
    active_run = 0

    collecting = False
    segment = []
    idle_run = 0
    last_active_index = -1

    while True:
        sample = imu.read_accel_gyro()
        active = is_active(sample)

        # -------------------------------------------------
        # 아직 동작 시작 전
        # -------------------------------------------------
        if not collecting:
            history.append(sample)

            # history가 너무 커지지 않도록 유지
            max_history = PAD_BEFORE + MIN_ACTIVE_SAMPLES + 5
            if len(history) > max_history:
                history.pop(0)

            if active:
                active_run += 1
            else:
                active_run = 0

            # 너무 짧은 흔들림은 무시하고,
            # active가 일정 샘플 이상 이어졌을 때 동작 시작으로 인정
            if active_run >= MIN_ACTIVE_SAMPLES:
                print("동작 시작 감지")

                # active 시작 직전 PAD_BEFORE까지 포함
                keep_count = PAD_BEFORE + active_run
                if keep_count > len(history):
                    keep_count = len(history)

                segment = history[-keep_count:]

                collecting = True
                idle_run = 0
                last_active_index = len(segment) - 1

                led.on()

        # -------------------------------------------------
        # 동작 수집 중
        # -------------------------------------------------
        else:
            segment.append(sample)

            if active:
                idle_run = 0
                last_active_index = len(segment) - 1
            else:
                idle_run += 1

            # 충분히 idle이 이어지면 동작 종료로 판단
            if idle_run >= MIN_IDLE_SAMPLES:
                led.off()

                end_index = last_active_index + 1 + PAD_AFTER
                if end_index > len(segment):
                    end_index = len(segment)

                segment = segment[:end_index]

                print("동작 종료")
                print("수집된 원본 샘플 수 =", len(segment))

                return segment

            # 너무 길게 잡히면 강제로 종료
            if len(segment) >= MAX_SEGMENT_SAMPLES:
                led.off()
                print("동작 구간이 너무 길어 강제 종료")
                print("수집된 원본 샘플 수 =", len(segment))
                return segment

        time.sleep_ms(SAMPLE_INTERVAL_MS)


# =========================================================
# 메인
# =========================================================
def main():
    print("Pico Gesture kNN Inference Start")

    if FEATURE_COUNT != TARGET_LEN * 6:
        print("[오류] FEATURE_COUNT와 TARGET_LEN이 맞지 않습니다.")
        print("FEATURE_COUNT =", FEATURE_COUNT)
        print("TARGET_LEN * 6 =", TARGET_LEN * 6)
        return

    i2c = I2C(
        I2C_ID,
        sda=Pin(SDA_PIN),
        scl=Pin(SCL_PIN),
        freq=I2C_FREQ
    )

    print("I2C scan =", [hex(x) for x in i2c.scan()])

    imu = LSM6DS3(i2c, addr=IMU_ADDR)

    while True:
        # 1. 실시간 센서 데이터에서 동작 구간 하나 수집
        segment = collect_one_gesture(imu)

        # 2. 84개 포인트로 리샘플링
        sample_84x6 = resample_segment(segment, TARGET_LEN)

        # 3. 84 x 6을 504개 입력 벡터로 변환
        raw_x = flatten_sample(sample_84x6)

        print("입력 feature 수 =", len(raw_x))

        if len(raw_x) != FEATURE_COUNT:
            print("[오류] 입력 feature 수가 모델과 맞지 않습니다.")
            continue

        # 4. 정규화 + kNN 거리 계산 + 분류
        pred, neighbors = predict_debug(raw_x)

        # 5. 결과 출력
        print()
        print("====================================")
        print("예측 결과:", pred)
        print("가까운 이웃:")
        for dist, label in neighbors:
            print("  ", label, "dist =", round(dist, 3))
        print("====================================")

        time.sleep_ms(COOLDOWN_MS)


main()
