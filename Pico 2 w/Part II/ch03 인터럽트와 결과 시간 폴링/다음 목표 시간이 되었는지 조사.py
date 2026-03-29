from machine import Pin
import time

green_led = Pin("LED", Pin.OUT)
green_led.value(0)
next_toggle = time.ticks_add(time.ticks_ms(), 1000)

while True:
    now = time.ticks_ms()
    if time.ticks_diff(now, next_toggle) >= 0:
        green_led.toggle()
        next_toggle = time.ticks_add(next_toggle, 1000)
