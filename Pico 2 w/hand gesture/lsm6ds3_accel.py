from machine import Pin, I2C
from time import sleep_ms
# lsm6ds3 모듈을 Raspberry Pi Pico 2 W 보드에 업로드 되어 있어야 함
from lsm6ds3 import LSM6DS3

i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400_000)
imu = LSM6DS3(i2c)

if not imu.begin():
    raise RuntimeError('LSM6DS3 초기화 실패')

# 20ms 주기로 
# LSM6DS3 센서로부터 값을 읽어와서 3축 가속도와 3축 자이로 값을 update 함
# 3축 가속도 값만 출력함

while True:
    ax, ay, az, gx, gy, gz = imu.update()
    print("{:+.1f}, {:+.1f}, {:+.1f}".format(ax, ay, az))
    sleep_ms(20)
