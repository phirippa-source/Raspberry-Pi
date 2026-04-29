# main.py
import network
import socket
import time
from machine import ADC, Pin


# ------------------------------------------------------------
# Wi-Fi AP 설정
# ------------------------------------------------------------

SSID = "PICO2W-OPEN"

# Pico가 UDP 명령을 받을 포트
PICO_PORT = 5005

# ADC 데이터를 보내는 주기
# 50ms = 1초에 약 20번 전송
SEND_INTERVAL_MS = 50


# ------------------------------------------------------------
# ADC2 설정
# ------------------------------------------------------------

# Raspberry Pi Pico 2 W에서
# GP28 핀은 ADC2 입력으로 사용할 수 있다.
#
# 가변저항 가운데 핀을 GP28에 연결했다고 가정한다.
adc = ADC(Pin(28))


def read_adc2():
    """
    ADC2 값을 읽어서 raw 값과 전압값을 반환한다.

    raw:
        0 ~ 65535 범위의 ADC 값

    voltage:
        0.0 ~ 3.3V 근처의 전압값
    """
    raw = adc.read_u16()
    voltage = raw * 3.3 / 65535
    return raw, voltage


# ------------------------------------------------------------
# STA 모드 끄기
# ------------------------------------------------------------

# STA 모드는 Pico가 다른 공유기에 접속하는 모드이다.
# 지금은 Pico가 직접 Wi-Fi AP가 되어야 하므로 STA 모드는 끈다.
sta = network.WLAN(network.WLAN.IF_STA)
sta.active(False)
time.sleep(1)


# ------------------------------------------------------------
# AP 모드 설정
# ------------------------------------------------------------

# AP 모드는 Pico가 직접 Wi-Fi를 만들어내는 모드이다.
ap = network.WLAN(network.WLAN.IF_AP)

# 혹시 이전 AP 설정이 남아 있을 수 있으므로 먼저 꺼 준다.
ap.active(False)
time.sleep(1)

# 암호 없는 AP 설정
ap.config(
    ssid=SSID,
    security=0,     # 0 = 암호 없음
    channel=6
)

# AP 켜기
ap.active(True)

# AP가 완전히 켜질 때까지 대기
while not ap.active():
    time.sleep(0.1)

print("Open Access Point started")
print("SSID:", SSID)
print("IP config:", ap.ifconfig())


# ------------------------------------------------------------
# UDP 소켓 설정
# ------------------------------------------------------------

# UDP 소켓 생성
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Pico가 UDP 5005번 포트에서 데이터를 받을 수 있게 한다.
sock.bind(("0.0.0.0", PICO_PORT))

# 매우 중요:
# non-blocking 모드로 설정한다.
#
# 이렇게 해야 노트북에서 데이터가 오지 않아도
# Pico가 recvfrom()에서 멈추지 않고 계속 ADC를 읽을 수 있다.
sock.setblocking(False)

print("UDP ready on port", PICO_PORT)


# ------------------------------------------------------------
# 노트북 주소 저장 변수
# ------------------------------------------------------------

# 처음에는 노트북 주소를 모른다.
# 노트북이 HELLO를 보내면 그때 addr을 저장한다.
notebook_addr = None

# 마지막으로 ADC 데이터를 보낸 시간
last_send_time = time.ticks_ms()


# ------------------------------------------------------------
# Main loop
# ------------------------------------------------------------

while True:

    # --------------------------------------------------------
    # 1. 노트북에서 HELLO가 왔는지 확인
    # --------------------------------------------------------

    try:
        # non-blocking 모드이므로,
        # 데이터가 없으면 바로 OSError가 발생하고 지나간다.
        data, addr = sock.recvfrom(1024)

        msg = data.decode().strip()
        print("Received:", msg, "from", addr)

        # 노트북이 HELLO를 보내면
        # Pico는 노트북의 IP 주소와 포트 번호를 기억한다.
        if msg.upper() == "HELLO":
            notebook_addr = addr
            print("Notebook registered:", notebook_addr)

            # 등록 확인 응답
            sock.sendto(b"PICO_READY", notebook_addr)

    except OSError:
        # 수신된 UDP 데이터가 없으면 여기로 온다.
        # 정상적인 상황이므로 아무 일도 하지 않는다.
        pass


    # --------------------------------------------------------
    # 2. 노트북 주소를 알고 있으면 ADC 값을 주기적으로 전송
    # --------------------------------------------------------

    now = time.ticks_ms()

    if notebook_addr is not None:
        if time.ticks_diff(now, last_send_time) >= SEND_INTERVAL_MS:
            last_send_time = now

            raw, voltage = read_adc2()

            # CSV 형식으로 데이터 구성
            #
            # 형식:
            #   시간(ms), ADC raw 값, 전압값
            #
            # 예:
            #   123456,32768,1.650
            payload = "{},{},{:.3f}".format(now, raw, voltage)

            try:
                sock.sendto(payload.encode(), notebook_addr)
            except OSError as e:
                print("Send error:", e)


    # CPU를 너무 바쁘게 쓰지 않도록 아주 짧게 쉰다.
    time.sleep_ms(1)
