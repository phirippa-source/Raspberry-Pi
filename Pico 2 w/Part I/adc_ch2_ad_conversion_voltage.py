from machine import ADC, Pin
import time

adc2 = ADC( Pin(28) )

while True:
    adc_value = adc2.read_u16()
    v = adc_value * 3.3/65536.0
    print(f'adc_value: {adc_value}\tv: {v:.2f}')
    time.sleep_ms(200)
