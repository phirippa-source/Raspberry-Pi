from machine import Pin, I2C
from time import sleep_ms
from lsm6ds3 import LSM6DS3

i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400_000)
imu = LSM6DS3(i2c)
if not imu.begin(accel_range=2, gyro_range=250, odr_hz=104):
    raise RuntimeError('LSM6DS3 초기화 실패')

print('자이로 영점 보정 시작. 센서를 잠시 가만히 두세요...')
offx, offy, offz = imu.calibrateGyro(samples=200, delay_ms=5)
print("자이로 오프셋:", offx, offy, offz)


while True:
    ax, ay, az, gx, gy, gz = imu.update()
    print(
        "ACC[g]: ({:+.1f}, {:+.1f}, {:+.1f}) | "
        "GYRO[dps]: ({:+.4f}, {:+.4f}, {:+.4f})".format(ax, ay, az, gx, gy, gz)
        )
    sleep_ms(20)
