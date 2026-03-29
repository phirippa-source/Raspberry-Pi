from machine import Pin
import time

green_led = Pin("LED", Pin.OUT)
green_led.value(0)
last_toggle = time.ticks_ms()

while True:
    now = time.ticks_ms()
    if time.ticks_diff(now, last_toggle) >= 1000:
        green_led.toggle()
        last_toggle = now
