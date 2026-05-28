# ria_z_ble_car.py
# BLE RC car control module for Raspberry Pi Pico 2 W
#
# This module hides BLE scan, connection, service discovery,
# characteristic discovery, and BLE write logic.
#
# Student-facing usage:
#
#     from ria_z_ble_car import PaiZCar
#
#     TEAM_ID = 7
#
#     car = PaiZCar(TEAM_ID)
#     car.connect()
#
#     car.command("F", 1000)
#     car.command("S", 500)


import bluetooth
import time
from micropython import const


# =========================================================
# BLE UUIDs
# Must be the same as the Arduino UNO R4 WiFi code.
# =========================================================
_SERVICE_UUID = bluetooth.UUID("19b10000-e8f2-537e-4f6c-d104768a1214")
_COMMAND_UUID = bluetooth.UUID("19b10001-e8f2-537e-4f6c-d104768a1214")


# =========================================================
# BLE IRQ event constants
# =========================================================
_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)
_IRQ_PERIPHERAL_CONNECT = const(7)
_IRQ_PERIPHERAL_DISCONNECT = const(8)
_IRQ_GATTC_SERVICE_RESULT = const(9)
_IRQ_GATTC_SERVICE_DONE = const(10)
_IRQ_GATTC_CHARACTERISTIC_RESULT = const(11)
_IRQ_GATTC_CHARACTERISTIC_DONE = const(12)
_IRQ_GATTC_WRITE_DONE = const(17)


def _decode_name(adv_data):
    """
    Decode BLE advertising data and return the device name.

    This function is used internally by the module.
    Students do not need to use this function directly.
    """
    i = 0
    data = bytes(adv_data)

    while i + 1 < len(data):
        length = data[i]

        if length == 0:
            break

        ad_type = data[i + 1]

        # 0x08: Shortened Local Name
        # 0x09: Complete Local Name
        if ad_type == 0x08 or ad_type == 0x09:
            name_bytes = data[i + 2 : i + 1 + length]

            try:
                return name_bytes.decode()
            except:
                return None

        i += 1 + length

    return None


class PaiZCar:
    """
    BLE client class for the Physical AI RC Car.

    The target car must be an Arduino UNO R4 WiFi BLE peripheral.

    BLE device name format:
        RIA_Z_01
        RIA_Z_02
        ...
        RIA_Z_18

    Command packet format:
        "07:F"
        "07:L"
        "07:R"
        "07:S"

    Student-facing usage:

        from ria_z_ble_car import PaiZCar

        TEAM_ID = 7

        car = PaiZCar(TEAM_ID)
        car.connect()

        car.command("F", 1000)
        car.command("S", 500)
    """

    def __init__(self, team_id):
        if team_id < 1 or team_id > 99:
            raise ValueError("TEAM_ID must be between 1 and 99")

        self.team_id = team_id

        # Example:
        #   TEAM_ID = 7 -> RIA_Z_07
        self.target_name = "RIA_Z_%02d" % team_id

        self.ble = bluetooth.BLE()
        self.ble.active(True)
        self.ble.irq(self._irq)

        self._reset()

    def _reset(self):
        self.addr_type = None
        self.addr = None

        self.conn_handle = None
        self.connected = False

        self.service_start = None
        self.service_end = None
        self.service_found = False
        self.service_done = False

        self.cmd_handle = None
        self.char_found = False
        self.char_done = False

        self.write_done = False
        self.write_status = None

    def _irq(self, event, data):
        if event == _IRQ_SCAN_RESULT:
            addr_type, addr, adv_type, rssi, adv_data = data
            name = _decode_name(adv_data)

            if name == self.target_name and self.addr is None:
                print("Found:", name, "RSSI:", rssi)

                self.addr_type = addr_type
                self.addr = bytes(addr)

                # Stop scanning after finding the target car.
                self.ble.gap_scan(None)

        elif event == _IRQ_SCAN_DONE:
            pass

        elif event == _IRQ_PERIPHERAL_CONNECT:
            conn_handle, addr_type, addr = data

            if self.addr == bytes(addr):
                self.conn_handle = conn_handle
                self.connected = True
                print("Connected to", self.target_name)

        elif event == _IRQ_PERIPHERAL_DISCONNECT:
            conn_handle, addr_type, addr = data
            print("Disconnected")
            self._reset()

        elif event == _IRQ_GATTC_SERVICE_RESULT:
            conn_handle, start_handle, end_handle, uuid = data

            if uuid == _SERVICE_UUID:
                self.service_start = start_handle
                self.service_end = end_handle
                self.service_found = True
                print("Service found")

        elif event == _IRQ_GATTC_SERVICE_DONE:
            conn_handle, status = data
            self.service_done = True

        elif event == _IRQ_GATTC_CHARACTERISTIC_RESULT:
            conn_handle, def_handle, value_handle, properties, uuid = data

            if uuid == _COMMAND_UUID:
                self.cmd_handle = value_handle
                self.char_found = True
                print("Command characteristic found")

        elif event == _IRQ_GATTC_CHARACTERISTIC_DONE:
            conn_handle, status = data
            self.char_done = True

        elif event == _IRQ_GATTC_WRITE_DONE:
            conn_handle, value_handle, status = data
            self.write_done = True
            self.write_status = status

    def _wait_until(self, condition_func, timeout_ms, error_message):
        start = time.ticks_ms()

        while not condition_func():
            if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
                raise RuntimeError(error_message)

            time.sleep_ms(20)

    def connect(self):
        """
        Scan and connect to the target RC car.

        Example:
            TEAM_ID = 7
            Target BLE name = RIA_Z_07
        """
        print("Team ID:", self.team_id)
        print("Target car:", self.target_name)
        print("Scanning...")

        self._reset()

        # Active scan is important because the BLE local name may be
        # included in scan response data.
        self.ble.gap_scan(8000, 30000, 30000, True)

        self._wait_until(
            lambda: self.addr is not None,
            9000,
            "Target car not found: " + self.target_name
        )

        time.sleep_ms(300)

        print("Connecting...")
        self.ble.gap_connect(self.addr_type, self.addr)

        self._wait_until(
            lambda: self.connected,
            5000,
            "BLE connection failed"
        )

        print("Discovering services...")
        self.ble.gattc_discover_services(self.conn_handle)

        self._wait_until(
            lambda: self.service_done,
            5000,
            "Service discovery timeout"
        )

        if not self.service_found:
            raise RuntimeError("Required service not found")

        print("Discovering characteristics...")
        self.ble.gattc_discover_characteristics(
            self.conn_handle,
            self.service_start,
            self.service_end
        )

        self._wait_until(
            lambda: self.char_done,
            5000,
            "Characteristic discovery timeout"
        )

        if not self.char_found:
            raise RuntimeError("Command characteristic not found")

        print("Ready")

    def _write_command(self, cmd):
        """
        Send one BLE command packet.

        Example:
            TEAM_ID = 7
            cmd = "F"
            packet = "07:F"
        """
        if not self.connected:
            raise RuntimeError("Not connected")

        packet = "%02d:%s" % (self.team_id, cmd)

        self.write_done = False
        self.write_status = None

        # mode = 1: write with response
        # This generates _IRQ_GATTC_WRITE_DONE after the write response.
        self.ble.gattc_write(
            self.conn_handle,
            self.cmd_handle,
            packet.encode(),
            1
        )

        self._wait_until(
            lambda: self.write_done,
            2000,
            "BLE write timeout"
        )

        if self.write_status != 0:
            raise RuntimeError("BLE write failed, status=" + str(self.write_status))

        print("Send:", packet)

    def command(self, cmd, duration_ms=300, period_ms=100):
        """
        Send a car command repeatedly for a certain duration.

        cmd:
            "F" : Forward
            "L" : Left
            "R" : Right
            "S" : Stop

        duration_ms:
            How long the command should be sent.

        period_ms:
            Command repeat period.
            Default is 100 ms.

        Example:
            car.command("F", 1000)
            -> Send forward command repeatedly for 1000 ms.

            car.command("S", 500)
            -> Send stop command repeatedly for 500 ms.
        """
        cmd = cmd.upper()

        if cmd not in ("F", "L", "R", "S"):
            raise ValueError("Invalid command: " + cmd)

        start = time.ticks_ms()

        while time.ticks_diff(time.ticks_ms(), start) < duration_ms:
            self._write_command(cmd)
            time.sleep_ms(period_ms)

    def stop(self, duration_ms=300):
        """
        Stop the car.

        Example:
            car.stop()
            car.stop(1000)
        """
        self.command("S", duration_ms)
