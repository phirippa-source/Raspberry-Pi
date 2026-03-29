from machine import Pin
import time

green_led = Pin("LED", Pin.OUT)
red_led = Pin(15, Pin.OUT)
button = Pin(14, Pin.IN)

while True:
    green_led.value(1)
    time.sleep(1)
    green_led.value(0)
    time.sleep(1)
    
    state = button.value()
    red_led.value(state)
