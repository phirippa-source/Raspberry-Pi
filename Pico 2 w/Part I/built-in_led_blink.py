from machine import Pin    # machine 모듈에서 Pin 클래스를 가져옴
import time

led = Pin('LED', Pin.OUT)

while True:
  led.value(1)
  time.sleep(1)

  led.value(0)
  time.sleep(1)
