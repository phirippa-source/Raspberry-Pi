#include <ArduinoBLE.h>

const char* TARGET_NAME = "sunmoon-8086";
const char* CHAR_UUID   = "12345678-1234-1234-1234-1234567890AC";

BLEDevice pico;
BLECharacteristic numberChar;

unsigned long prevMs = 0;

void setup() {
  Serial.begin(115200);
  delay(1000);

  if (!BLE.begin()) {
    Serial.println("BLE 시작 실패");
    while (1);
  }

  BLE.scan();
  Serial.println("스캔 시작");
}

void loop() {
  if (!pico) {
    BLEDevice dev = BLE.available();

    if (dev && dev.localName() == TARGET_NAME) {
      BLE.stopScan();

      if (dev.connect()) {
        Serial.println("연결 성공");

        if (dev.discoverAttributes()) {
          numberChar = dev.characteristic(CHAR_UUID);

          if (numberChar) {
            pico = dev;
            Serial.println("읽기 준비 완료");
          } else {
            Serial.println("characteristic 못 찾음");
            dev.disconnect();
            BLE.scan();
          }
        } else {
          Serial.println("속성 탐색 실패");
          dev.disconnect();
          BLE.scan();
        }
      } else {
        Serial.println("연결 실패");
        BLE.scan();
      }
    }

    return;
  }

  if (!pico.connected()) {
    Serial.println("연결 끊김");
    pico = BLEDevice();
    BLE.scan();
    return;
  }

  if (millis() - prevMs >= 1000) {
    prevMs = millis();

    byte value;
    if (numberChar.readValue(value)) {
      Serial.print("받은 값: ");
      Serial.println(value);
    }
  }
}
