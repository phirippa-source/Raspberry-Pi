from machine import Pin, I2C
import time

# I2C 0번 채널을 사용하고 있다고 가정함(SDA=GP0, SCL=GP1)
i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=100000)
time.sleep_ms(100)        # I2C 채널 안정화 시간

addrs = i2c.scan()
if addrs:
    print("I2C scan =", [hex(a) for a in addrs])
else:
    print("I2C 장치가 발견되지 않았습니다.")
