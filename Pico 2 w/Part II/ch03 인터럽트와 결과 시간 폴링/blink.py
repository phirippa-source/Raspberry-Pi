from machine import Pin
import time

green_led = Pin("LED", Pin.OUT)

while True:
    green_led.value(1)
    time.sleep(1)
    
    green_led.value(0)
    time.sleep(1)
