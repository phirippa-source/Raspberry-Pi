# ria_servo.py
from machine import Pin, PWM

class ServoSG90:
    """
    SG90(또는 유사 50Hz 서보)용 간단 클래스
    학생들은 write(deg)만 사용하면 됨.
    """
    def __init__(self, gpio: int, min_us: int = 500, max_us: int = 2400, freq: int = 50):
        self._pwm = PWM(Pin(gpio))
        self._pwm.freq(freq)
        self._min_us = int(min_us)
        self._max_us = int(max_us)

    def write(self, deg: float):
        """deg(0~180)를 넣으면 서보를 해당 각도로 이동"""
        if deg < 0:
            deg = 0
        elif deg > 180:
            deg = 180

        us = self._min_us + (self._max_us - self._min_us) * (deg / 180.0)
        self._pwm.duty_ns(int(us * 1000))  # microseconds -> nanoseconds

    def deinit(self):
        self._pwm.deinit()

