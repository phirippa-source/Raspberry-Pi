from time import sleep_ms
from math import atan2, sqrt, pi


class LSM6DS3:
    REG_WHO_AM_I  = 0x0F
    REG_CTRL1_XL  = 0x10
    REG_CTRL2_G   = 0x11
    REG_CTRL3_C   = 0x12

    REG_OUTX_L_G  = 0x22
    REG_OUTX_L_XL = 0x28

    WHO_AM_I_OK = (0x69, 0x6A)

    _ACCEL_FS_BITS = {
        2:  0b00,
        4:  0b10,
        8:  0b11,
        16: 0b01,
    }

    _ACCEL_SENS_MG = {
        2:  0.061,
        4:  0.122,
        8:  0.244,
        16: 0.488,
    }

    _ACCEL_ODR_BITS = {
        0:      0b0000,
        12.5:   0b0001,
        26:     0b0010,
        52:     0b0011,
        104:    0b0100,
        208:    0b0101,
        416:    0b0110,
        833:    0b0111,
        1660:   0b1000,
        3330:   0b1001,
        6660:   0b1010,
    }

    _GYRO_FS_BITS = {
        125:  {"fs_g": 0b00, "fs_125": 1},
        250:  {"fs_g": 0b00, "fs_125": 0},
        500:  {"fs_g": 0b01, "fs_125": 0},
        1000: {"fs_g": 0b10, "fs_125": 0},
        2000: {"fs_g": 0b11, "fs_125": 0},
    }

    _GYRO_SENS_MDPS = {
        125:  4.375,
        250:  8.75,
        500:  17.50,
        1000: 35.0,
        2000: 70.0,
    }

    _GYRO_ODR_BITS = {
        0:      0b0000,
        12.5:   0b0001,
        26:     0b0010,
        52:     0b0011,
        104:    0b0100,
        208:    0b0101,
        416:    0b0110,
        833:    0b0111,
        1660:   0b1000,
    }

    _COMMON_ODRS = (0, 12.5, 26, 52, 104, 208, 416, 833, 1660)

    def __init__(self, i2c, addr=0x6B):
        self.i2c = i2c
        self.addr = addr

        self._accel_range = 2
        self._accel_odr = 104
        self._accel_sens_mg = self._ACCEL_SENS_MG[self._accel_range]

        self._gyro_range = 250
        self._gyro_odr = 104
        self._gyro_sens_mdps = self._GYRO_SENS_MDPS[self._gyro_range]

        self._ax = 0.0
        self._ay = 0.0
        self._az = 0.0

        self._gx = 0.0
        self._gy = 0.0
        self._gz = 0.0

        self._gyro_offset_x = 0.0
        self._gyro_offset_y = 0.0
        self._gyro_offset_z = 0.0

        self._begun = False

    def _write_u8(self, reg, val):
        self.i2c.writeto_mem(self.addr, reg, bytes([val & 0xFF]))

    def _read_u8(self, reg):
        return self.i2c.readfrom_mem(self.addr, reg, 1)[0]

    def _read_block(self, reg, length):
        return self.i2c.readfrom_mem(self.addr, reg, length)

    @staticmethod
    def _to_int16(lo, hi):
        v = (hi << 8) | lo
        if v & 0x8000:
            v -= 65536
        return v

    def whoAmI(self):
        return self._read_u8(self.REG_WHO_AM_I)

    def who_am_i(self):
        return self.whoAmI()

    def begin(self, accel_range=2, gyro_range=250, odr_hz=104):
        try:
            who = self.whoAmI()
        except Exception:
            return False

        if who not in self.WHO_AM_I_OK:
            return False

        if odr_hz not in self._COMMON_ODRS:
            raise ValueError(
                "begin()의 odr_hz는 0, 12.5, 26, 52, 104, 208, 416, 833, 1660 중 하나여야 합니다."
            )

        self.setAccelRange(accel_range)
        self.setGyroRange(gyro_range)
        self.setAccelODR(odr_hz)
        self.setGyroODR(odr_hz)

        self._write_u8(self.REG_CTRL3_C, 0x44)

        self._apply_ctrl1_xl()
        self._apply_ctrl2_g()

        sleep_ms(20)
        self._begun = True
        return True

    def setAccelRange(self, g):
        if g not in self._ACCEL_FS_BITS:
            raise ValueError("가속도 범위는 2, 4, 8, 16 중 하나여야 합니다.")

        self._accel_range = g
        self._accel_sens_mg = self._ACCEL_SENS_MG[g]

        if self._begun:
            self._apply_ctrl1_xl()

    def setAccelODR(self, odr_hz):
        if odr_hz not in self._ACCEL_ODR_BITS:
            raise ValueError(
                "가속도 ODR은 0, 12.5, 26, 52, 104, 208, 416, 833, 1660, 3330, 6660 중 하나여야 합니다."
            )

        self._accel_odr = odr_hz

        if self._begun:
            self._apply_ctrl1_xl()

    def setGyroRange(self, dps):
        if dps not in self._GYRO_FS_BITS:
            raise ValueError("자이로 범위는 125, 250, 500, 1000, 2000 중 하나여야 합니다.")

        self._gyro_range = dps
        self._gyro_sens_mdps = self._GYRO_SENS_MDPS[dps]

        if self._begun:
            self._apply_ctrl2_g()

    def setGyroODR(self, odr_hz):
        if odr_hz not in self._GYRO_ODR_BITS:
            raise ValueError(
                "자이로 ODR은 0, 12.5, 26, 52, 104, 208, 416, 833, 1660 중 하나여야 합니다."
            )

        self._gyro_odr = odr_hz

        if self._begun:
            self._apply_ctrl2_g()

    def _apply_ctrl1_xl(self):
        fs_bits = self._ACCEL_FS_BITS[self._accel_range]
        odr_bits = self._ACCEL_ODR_BITS[self._accel_odr]
        ctrl1_xl = (odr_bits << 4) | (fs_bits << 2)
        self._write_u8(self.REG_CTRL1_XL, ctrl1_xl)

    def _apply_ctrl2_g(self):
        cfg = self._GYRO_FS_BITS[self._gyro_range]
        odr_bits = self._GYRO_ODR_BITS[self._gyro_odr]
        fs_g = cfg["fs_g"]
        fs_125 = cfg["fs_125"]
        ctrl2_g = (odr_bits << 4) | (fs_g << 2) | (fs_125 << 1)
        self._write_u8(self.REG_CTRL2_G, ctrl2_g)

    def readAccelerationRaw(self):
        data = self._read_block(self.REG_OUTX_L_XL, 6)
        ax = self._to_int16(data[0], data[1])
        ay = self._to_int16(data[2], data[3])
        az = self._to_int16(data[4], data[5])
        return ax, ay, az

    def readAcceleration(self):
        ax_raw, ay_raw, az_raw = self.readAccelerationRaw()
        scale = self._accel_sens_mg / 1000.0
        self._ax = ax_raw * scale
        self._ay = ay_raw * scale
        self._az = az_raw * scale
        return self._ax, self._ay, self._az

    def readGyroRaw(self):
        data = self._read_block(self.REG_OUTX_L_G, 6)
        gx = self._to_int16(data[0], data[1])
        gy = self._to_int16(data[2], data[3])
        gz = self._to_int16(data[4], data[5])
        return gx, gy, gz

    def readGyro(self):
        gx_raw, gy_raw, gz_raw = self.readGyroRaw()
        scale = self._gyro_sens_mdps / 1000.0

        gx = gx_raw * scale
        gy = gy_raw * scale
        gz = gz_raw * scale

        self._gx = gx - self._gyro_offset_x
        self._gy = gy - self._gyro_offset_y
        self._gz = gz - self._gyro_offset_z

        return self._gx, self._gy, self._gz

    def readGyroscopeRaw(self):
        return self.readGyroRaw()

    def readGyroscope(self):
        return self.readGyro()

    def calibrateGyro(self, samples=200, delay_ms=5):
        if not self._begun:
            raise RuntimeError("먼저 begin()을 호출해야 합니다.")

        if samples <= 0:
            raise ValueError("samples는 1 이상이어야 합니다.")

        self._gyro_offset_x = 0.0
        self._gyro_offset_y = 0.0
        self._gyro_offset_z = 0.0

        sum_x = 0.0
        sum_y = 0.0
        sum_z = 0.0

        scale = self._gyro_sens_mdps / 1000.0

        sleep_ms(100)

        for _ in range(samples):
            gx_raw, gy_raw, gz_raw = self.readGyroRaw()
            sum_x += gx_raw * scale
            sum_y += gy_raw * scale
            sum_z += gz_raw * scale
            sleep_ms(delay_ms)

        self._gyro_offset_x = sum_x / samples
        self._gyro_offset_y = sum_y / samples
        self._gyro_offset_z = sum_z / samples

        return self._gyro_offset_x, self._gyro_offset_y, self._gyro_offset_z

    def resetGyroCalibration(self):
        self._gyro_offset_x = 0.0
        self._gyro_offset_y = 0.0
        self._gyro_offset_z = 0.0

    def update(self):
        self.readAcceleration()
        self.readGyro()
        return self._ax, self._ay, self._az, self._gx, self._gy, self._gz

    def getPitchRollFromAccel(self):
        ax = self._ax
        ay = self._ay
        az = self._az

        roll = atan2(ay, az) * 180.0 / pi
        pitch = atan2(-ax, sqrt(ay * ay + az * az)) * 180.0 / pi

        return pitch, roll

    def help(self):
        print("""
[LSM6DS3 주요 함수 안내]

1) begin(accel_range=2, gyro_range=250, odr_hz=104)
   - 용도: 센서를 초기화하고 시작 설정값을 적용합니다.
   - 매개변수:
     accel_range = 가속도 범위 (2, 4, 8, 16)
     gyro_range  = 자이로 범위 (125, 250, 500, 1000, 2000)
     odr_hz      = 가속도/자이로 공통 ODR
                   (0, 12.5, 26, 52, 104, 208, 416, 833, 1660)
   - 반환값:
     True  = 초기화 성공
     False = 초기화 실패

2) whoAmI() / who_am_i()
   - 용도: 센서 ID를 읽습니다.
   - 매개변수: 없음
   - 반환값: 정수 ID 값 (예: 0x69 또는 0x6A)

3) setAccelRange(g)
   - 용도: 가속도 측정 범위를 바꿉니다.
   - 매개변수: g = 2, 4, 8, 16
   - 반환값: 없음

4) setGyroRange(dps)
   - 용도: 자이로 측정 범위를 바꿉니다.
   - 매개변수: dps = 125, 250, 500, 1000, 2000
   - 반환값: 없음

5) setAccelODR(odr_hz)
   - 용도: 가속도 ODR을 바꿉니다.
   - 매개변수: odr_hz = 0, 12.5, 26, 52, 104, 208, 416, 833, 1660, 3330, 6660
   - 반환값: 없음

6) setGyroODR(odr_hz)
   - 용도: 자이로 ODR을 바꿉니다.
   - 매개변수: odr_hz = 0, 12.5, 26, 52, 104, 208, 416, 833, 1660
   - 반환값: 없음

7) readAccelerationRaw()
   - 용도: 가속도 raw 값을 읽습니다.
   - 매개변수: 없음
   - 반환값: (ax_raw, ay_raw, az_raw)

8) readAcceleration()
   - 용도: 가속도 값을 g 단위로 읽습니다.
   - 매개변수: 없음
   - 반환값: (ax, ay, az) [g]

9) readGyroRaw() / readGyroscopeRaw()
   - 용도: 자이로 raw 값을 읽습니다.
   - 매개변수: 없음
   - 반환값: (gx_raw, gy_raw, gz_raw)

10) readGyro() / readGyroscope()
    - 용도: 자이로 값을 dps 단위로 읽습니다.
    - 매개변수: 없음
    - 반환값: (gx, gy, gz) [dps]
    - 참고: calibrateGyro()로 구한 오프셋이 반영됩니다.

11) calibrateGyro(samples=200, delay_ms=5)
    - 용도: 자이로 영점 보정을 수행합니다.
    - 매개변수:
      samples  = 샘플 수
      delay_ms = 샘플 간 대기 시간(ms)
    - 반환값: (offset_x, offset_y, offset_z)
    - 주의: 보정 중에는 센서를 가만히 두어야 합니다.

12) resetGyroCalibration()
    - 용도: 자이로 보정값을 0으로 초기화합니다.
    - 매개변수: 없음
    - 반환값: 없음

13) update()
    - 용도: 가속도/자이로 값을 한 번에 갱신합니다.
    - 매개변수: 없음
    - 반환값: (ax, ay, az, gx, gy, gz)

14) getPitchRollFromAccel()
    - 용도: 마지막 가속도 값으로 pitch, roll을 계산합니다.
    - 매개변수: 없음
    - 반환값: (pitch, roll) [deg]

15) getAccelerationX(), getAccelerationY(), getAccelerationZ()
    - 용도: 마지막 가속도 값을 축별로 가져옵니다.
    - 반환값: 각 축 가속도 [g]

16) getGyroX(), getGyroY(), getGyroZ()
    - 용도: 마지막 자이로 값을 축별로 가져옵니다.
    - 반환값: 각 축 각속도 [dps]

17) getAccelRange(), getAccelODR(), getGyroRange(), getGyroODR()
    - 용도: 현재 설정값을 확인합니다.
    - 반환값: 현재 설정된 값

18) getGyroOffsetX(), getGyroOffsetY(), getGyroOffsetZ()
    - 용도: 현재 자이로 오프셋을 확인합니다.
    - 반환값: 각 축 오프셋 [dps]

[기본 사용 예]
    imu = LSM6DS3(i2c)

    if imu.begin():
        imu.help()
        imu.calibrateGyro()
        ax, ay, az = imu.readAcceleration()
        gx, gy, gz = imu.readGyro()

[사용자 설정 예]
    imu = LSM6DS3(i2c)

    if imu.begin(accel_range=4, gyro_range=500, odr_hz=208):
        imu.help()
""")

    def getAccelerationX(self):
        return self._ax

    def getAccelerationY(self):
        return self._ay

    def getAccelerationZ(self):
        return self._az

    def getAccelRange(self):
        return self._accel_range

    def getAccelODR(self):
        return self._accel_odr

    def getGyroX(self):
        return self._gx

    def getGyroY(self):
        return self._gy

    def getGyroZ(self):
        return self._gz

    def getGyroscopeX(self):
        return self._gx

    def getGyroscopeY(self):
        return self._gy

    def getGyroscopeZ(self):
        return self._gz

    def getGyroRange(self):
        return self._gyro_range

    def getGyroODR(self):
        return self._gyro_odr

    def getGyroOffsetX(self):
        return self._gyro_offset_x

    def getGyroOffsetY(self):
        return self._gyro_offset_y

    def getGyroOffsetZ(self):
        return self._gyro_offset_z


LSM6DS = LSM6DS3
