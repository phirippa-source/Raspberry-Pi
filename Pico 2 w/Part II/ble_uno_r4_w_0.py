import bluetooth
import time

ble = bluetooth.BLE()
ble.active(True)

SERVICE_UUID = bluetooth.UUID("12345678-1234-1234-1234-1234567890AB")
CHAR_UUID    = bluetooth.UUID("12345678-1234-1234-1234-1234567890AC")

SERVICE = (
    SERVICE_UUID, ((CHAR_UUID, bluetooth.FLAG_READ),),
)

handles = ble.gatts_register_services((SERVICE,))
value_handle = handles[0][0]

# 광고 이름: PICO-NUM
adv = b"\x02\x01\x06\x0D\x09sunmoon-8086"
ble.gap_advertise(100, adv)

n = 1

while True:
    ble.gatts_write(value_handle, bytes([n]))
    print("Pico 값:", n)

    n += 1
    if n > 255:
        n = 1

    time.sleep(1)
