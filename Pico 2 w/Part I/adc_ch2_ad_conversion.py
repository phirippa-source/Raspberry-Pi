from machine import ADC, Pin
import time

adc2 = ADC( Pin(28) )

while True:
    adc_value = adc2.read_u16()
    print(adc_value)
    time.sleep_ms(200)
