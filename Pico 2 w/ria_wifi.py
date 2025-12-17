# ria_wifi.py (MicroPython / Pico 2 W)

import network
import time

class WiFiError(Exception):
    pass

class WiFiScanError(WiFiError):
    pass

class WiFiConnectError(WiFiError):
    pass


class AccessPoint:
    """주변에서 발견된 AP 1개를 표현하는 객체"""
    def __init__(self, ssid, ch, rssi, sec):
        self.ssid = ssid
        self.channel = ch
        self.rssi = rssi
        self.security = sec  # raw int

    @property
    def security_name(self):
        # MicroPython 문서 기준(0~4). 그 외는 UNKNOWN으로 처리.
        m = {
            0: "OPEN",
            1: "WEP",
            2: "WPA-PSK",
            3: "WPA2-PSK",
            4: "WPA/WPA2-PSK",
        }
        return m.get(self.security, "UNKNOWN(%d)" % self.security)

    def __repr__(self):
        return "AccessPoint(ssid=%r, ch=%d, rssi=%d, sec=%s)" % (
            self.ssid, self.channel, self.rssi, self.security_name
        )


class NetInfo:
    """연결 후 DHCP로 받은 네트워크 설정을 표현하는 객체"""
    def __init__(self, ip, netmask, gateway, dns):
        self.ip = ip
        self.netmask = netmask
        self.gateway = gateway
        self.dns = dns

    def __repr__(self):
        return "NetInfo(ip=%s, gw=%s, dns=%s)" % (self.ip, self.gateway, self.dns)


class RiaWiFi:
    """Wi-Fi 동작을 캡슐화한 메인 객체"""
    def __init__(self, pm=None):
        self._wlan = network.WLAN(network.STA_IF)
        self._wlan.active(True)

        if pm is not None:
            try:
                self._wlan.config(pm=pm)
            except:
                pass

        self._connected_ssid = None
        self._netinfo = None
        self._last_scan = []

    # ----- 상태(프로퍼티) -----
    @property
    def is_connected(self):
        return self._wlan.isconnected()

    @property
    def ssid(self):
        return self._connected_ssid

    @property
    def netinfo(self):
        """NetInfo 또는 None"""
        return self._netinfo

    @property
    def ip(self):
        return self._netinfo.ip if self._netinfo else None

    @property
    def gateway(self):
        return self._netinfo.gateway if self._netinfo else None

    @property
    def last_scan(self):
        """마지막 scan 결과 리스트[AccessPoint]"""
        return self._last_scan

    # ----- 기능(메서드) -----
    def scan(self, sort_by_rssi=True):
        """주변 AP 스캔 -> 리스트[AccessPoint] 반환 & 내부에 저장"""
        try:
            raw = self._wlan.scan()  # (ssid, bssid, channel, RSSI, security, hidden)
        except Exception as e:
            raise WiFiScanError("scan failed: %s" % e)

        aps = []
        for ssid_b, _bssid, ch, rssi, sec, _hidden in raw:
            ssid = ssid_b.decode("utf-8", "ignore") if ssid_b else "<hidden-ssid>"
            aps.append(AccessPoint(ssid, ch, rssi, sec))

        if sort_by_rssi:
            aps.sort(key=lambda ap: ap.rssi, reverse=True)

        self._last_scan = aps
        return aps

    def find(self, ssid):
        """마지막 scan 결과에서 SSID 일치하는 AP를 찾아 반환(없으면 None)"""
        for ap in self._last_scan:
            if ap.ssid == ssid:
                return ap
        return None

    def connect(self, ssid, password, timeout_s=15, precheck=False, auto_scan=True):
        """
        지정 SSID 접속 후 NetInfo 반환.
        - precheck=True: 접속 전 scan 결과로 SSID 존재 확인
        - auto_scan=True: precheck 시 scan 결과가 없으면 자동 scan
        """
        if precheck:
            if (not self._last_scan) and auto_scan:
                self.scan()
            if self.find(ssid) is None:
                raise WiFiConnectError("SSID not found in scan results: %s" % ssid)

        # 이전 연결 정리
        try:
            self._wlan.disconnect()
        except:
            pass

        self._wlan.connect(ssid, password)

        t0 = time.ticks_ms()
        while not self._wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), t0) > timeout_s * 1000:
                raise WiFiConnectError(
                    "connect timeout: ssid=%s, status=%s" % (ssid, self._wlan.status())
                )
            time.sleep(0.2)

        ip, netmask, gateway, dns = self._wlan.ifconfig()
        self._connected_ssid = ssid
        self._netinfo = NetInfo(ip, netmask, gateway, dns)
        return self._netinfo

    def ensure_connected(self, ssid, password, timeout_s=15):
        """
        이미 연결돼 있으면 그대로, 아니면 재연결.
        return: NetInfo
        """
        if self.is_connected and self._connected_ssid == ssid and self._netinfo:
            return self._netinfo
        return self.connect(ssid, password, timeout_s=timeout_s)

    def disconnect(self):
        try:
            self._wlan.disconnect()
        finally:
            self._connected_ssid = None
            self._netinfo = None

