# main.py

# network:
#   Pico 2 W의 Wi-Fi 기능을 사용하기 위한 모듈
#   AP 모드, STA 모드 설정에 사용한다.
import network

# socket:
#   UDP/TCP 네트워크 통신을 하기 위한 모듈
#   여기서는 UDP 통신을 위해 사용한다.
import socket

# time:
#   대기 시간 sleep()을 사용하기 위한 모듈
import time


# ------------------------------------------------------------
# Wi-Fi AP 설정값
# ------------------------------------------------------------

# Pico 2 W가 만들어 낼 Wi-Fi 이름
# 노트북에서는 Wi-Fi 목록에서 이 이름을 찾아 접속한다.
SSID = "PICO2W-OPEN"

# Pico 2 W가 UDP 데이터를 받을 포트 번호
# 노트북 쪽 코드에서도 이 포트 번호로 데이터를 보내야 한다.
PICO_PORT = 5005


# ------------------------------------------------------------
# STA 모드 끄기
# ------------------------------------------------------------

# STA 모드는 Pico 2 W가 다른 공유기에 접속하는 모드이다.
# 예:
#   Pico 2 W → Ria2G 공유기에 접속
#
# 지금은 Pico 2 W가 직접 Wi-Fi AP가 되어야 하므로
# STA 모드는 사용하지 않는다.
sta = network.WLAN(network.WLAN.IF_STA)

# STA 모드를 비활성화한다.
# 이전에 다른 공유기에 접속했던 상태가 남아 있을 수 있으므로
# 확실하게 꺼 주는 것이 좋다.
sta.active(False)

# Wi-Fi 상태가 안정적으로 바뀔 시간을 잠깐 준다.
time.sleep(1)


# ------------------------------------------------------------
# AP 모드 설정
# ------------------------------------------------------------

# AP 모드는 Pico 2 W가 직접 Wi-Fi 이름을 만들어 내는 모드이다.
# 예:
#   노트북 → PICO2W-OPEN에 접속
#
# 즉, Pico 2 W가 작은 공유기처럼 동작한다.
ap = network.WLAN(network.WLAN.IF_AP)

# 혹시 이전에 AP 모드가 켜져 있었다면 먼저 꺼 준다.
# 설정을 새로 적용하기 전에 초기화하는 의미이다.
ap.active(False)

# AP 모드가 꺼질 시간을 잠깐 준다.
time.sleep(1)


# ------------------------------------------------------------
# AP 세부 설정
# ------------------------------------------------------------

ap.config(
    # 노트북 Wi-Fi 목록에 표시될 이름
    ssid=SSID,

    # security=0은 암호 없는 공개 Wi-Fi를 의미한다.
    # 즉, 노트북에서 비밀번호 없이 접속한다.
    #
    # 참고:
    #   security=0 : 암호 없음, open
    #   security=3 : WPA2-PSK, 비밀번호 사용
    security=0,

    # Wi-Fi 채널 번호
    # 2.4GHz Wi-Fi에서 사용할 채널이다.
    # 보통 1, 6, 11 중 하나를 많이 사용한다.
    channel=6
)


# ------------------------------------------------------------
# AP 모드 켜기
# ------------------------------------------------------------

# Pico 2 W의 AP 모드를 활성화한다.
# 이 시점부터 노트북 Wi-Fi 목록에 PICO2W-OPEN이 보일 수 있다.
ap.active(True)


# AP가 완전히 켜질 때까지 기다린다.
# ap.active()가 True가 되면 AP 모드가 활성화된 상태이다.
while not ap.active():
    time.sleep(0.1)


# AP 시작 상태를 Thonny Shell에 출력한다.
print("Open Access Point started")
print("SSID:", SSID)

# ap.ifconfig()는 Pico 2 W AP의 네트워크 정보를 보여준다.
# 일반적으로 다음과 비슷하게 나온다.
#
# ('192.168.4.1', '255.255.255.0', '192.168.4.1', '8.8.8.8')
#
# 여기서 중요한 것은 첫 번째 값이다.
# 보통 Pico 2 W 자신의 IP 주소는 192.168.4.1 이다.
print("IP config:", ap.ifconfig())


# ------------------------------------------------------------
# UDP 소켓 열기
# ------------------------------------------------------------

# UDP 통신용 소켓을 만든다.
#
# socket.AF_INET:
#   IPv4 주소 체계를 사용한다는 뜻
#
# socket.SOCK_DGRAM:
#   UDP 통신을 사용한다는 뜻
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


# Pico 2 W가 UDP 데이터를 받을 주소와 포트를 지정한다.
#
# "0.0.0.0"은 특별한 의미를 가진 주소이다.
# Pico 2 W가 가진 모든 네트워크 인터페이스에서 오는 데이터를 받겠다는 뜻이다.
#
# PICO_PORT는 위에서 5005로 설정했다.
# 따라서 Pico 2 W는 UDP 5005번 포트에서 데이터를 기다린다.
sock.bind(("0.0.0.0", PICO_PORT))


print("UDP server ready on port", PICO_PORT)


# ------------------------------------------------------------
# UDP 수신 및 응답 반복
# ------------------------------------------------------------

# 계속 반복하면서 노트북에서 오는 UDP 데이터를 기다린다.
while True:

    # 노트북에서 UDP 데이터가 올 때까지 기다린다.
    #
    # recvfrom(1024):
    #   최대 1024바이트까지 데이터를 받는다.
    #
    # 반환값:
    #   data : 받은 데이터 내용, bytes 타입
    #   addr : 보낸 쪽 주소, 예: ('192.168.4.2', 6000)
    #
    # 주의:
    #   현재 코드는 blocking 방식이다.
    #   즉, 데이터가 들어올 때까지 이 줄에서 멈춰 기다린다.
    data, addr = sock.recvfrom(1024)

    # 받은 데이터는 bytes 타입이다.
    # 예: b'HELLO'
    #
    # decode():
    #   bytes를 문자열로 변환한다.
    #
    # strip():
    #   앞뒤 공백, 줄바꿈 문자 등을 제거한다.
    msg = data.decode().strip()


    # 받은 메시지와 보낸 쪽 주소를 출력한다.
    # 예:
    #   Received: HELLO from ('192.168.4.2', 6000)
    print("Received:", msg, "from", addr)


    # 노트북에서 보낸 메시지가 HELLO인지 확인한다.
    #
    # msg.upper():
    #   대문자로 변환한다.
    #
    # 따라서 노트북이 다음 중 무엇을 보내도 모두 HELLO로 인식한다.
    #   HELLO
    #   Hello
    #   hello
    if msg.upper() == "HELLO":

        # HELLO를 받으면 노트북으로 PICO_OK라고 응답한다.
        #
        # b"PICO_OK":
        #   문자열이 아니라 bytes 데이터이다.
        #
        # addr:
        #   방금 데이터를 보낸 노트북의 IP 주소와 포트 번호이다.
        #
        # 즉, "방금 나에게 HELLO를 보낸 노트북에게 답장을 보낸다"는 뜻이다.
        sock.sendto(b"PICO_OK", addr)

    else:
        # HELLO가 아닌 다른 메시지를 받으면
        # UNKNOWN_MESSAGE라고 응답한다.
        sock.sendto(b"UNKNOWN_MESSAGE", addr)
