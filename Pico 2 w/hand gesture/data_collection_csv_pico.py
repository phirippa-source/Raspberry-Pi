from machine import Pin, I2C
from time import sleep_ms, ticks_ms, ticks_diff
from lsm6ds3 import LSM6DS3

FILE_NAME = "gesture_log.csv"
DURATION_MS = 10000      # 10초 기록
SAMPLE_INTERVAL_MS = 10  # 약 100Hz

i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400_000)
imu = LSM6DS3(i2c)

if not imu.begin(accel_range=2, gyro_range=250, odr_hz=104):
    raise RuntimeError("LSM6DS3 초기화 실패")

print("자이로 영점 보정 시작. 센서를 가만히 두세요...")
offx, offy, offz = imu.calibrateGyro(samples=200, delay_ms=5)
print("자이로 오프셋:", offx, offy, offz)

print("CSV 저장 시작:", FILE_NAME)
print("기록 중에 손동작을 3~5번 반복해보세요.")

start_ms = ticks_ms()
next_ms = start_ms
count = 0

with open(FILE_NAME, "w") as f:
    f.write("t_ms,ax,ay,az,gx,gy,gz\n")

    while True:
        now_ms = ticks_ms()
        elapsed_ms = ticks_diff(now_ms, start_ms)

        if elapsed_ms >= DURATION_MS:
            break

        if ticks_diff(now_ms, next_ms) >= 0:
            ax, ay, az, gx, gy, gz = imu.update()
            line = "{},{:.6f},{:.6f},{:.6f},{:.6f},{:.6f},{:.6f}\n".format(
                elapsed_ms, ax, ay, az, gx, gy, gz
            )
            f.write(line)

            count += 1
            next_ms += SAMPLE_INTERVAL_MS
        else:
            sleep_ms(1)

print("저장 완료")
print("샘플 수 =", count)
print("파일 이름 =", FILE_NAME)
