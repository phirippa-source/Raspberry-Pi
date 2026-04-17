from machine import Pin
import time

led = Pin('LED', Pin.OUT)

count = 0
while count < 3:
    led.value(1)
    time.sleep(1)
    led.value(0)
    time.sleep(1)
    
    count = count + 1
    print(count)
