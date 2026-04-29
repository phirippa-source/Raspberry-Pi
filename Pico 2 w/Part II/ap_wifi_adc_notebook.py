# pc_adc2_monitor.py
import socket
import time


# ------------------------------------------------------------
# Pico 2 W 주소 설정
# ------------------------------------------------------------

# Pico 2 W가 AP 모드일 때 보통 자기 IP는 192.168.4.1이다.
PICO_IP = "192.168.4.1"

# Pico 코드에서 설정한 UDP 포트
PICO_PORT = 5005

# 노트북이 사용할 UDP 포트
# Pico는 노트북이 HELLO를 보낸 포트로 데이터를 다시 보낸다.
LOCAL_PORT = 6000


# ------------------------------------------------------------
# UDP 소켓 생성
# ------------------------------------------------------------

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# 노트북의 UDP 수신 포트를 6000번으로 고정한다.
sock.bind(("", LOCAL_PORT))

# 2초 동안 데이터가 안 오면 timeout 발생
sock.settimeout(2.0)


print("ADC2 UDP monitor started")
print("Local port:", LOCAL_PORT)
print("Pico target:", PICO_IP, PICO_PORT)


# ------------------------------------------------------------
# Pico에게 HELLO 전송
# ------------------------------------------------------------

# 이 HELLO는 "데이터 하나 보내줘"라는 요청이 아니다.
#
# 의미:
#   "Pico야, 내 IP와 포트는 여기야.
#    앞으로 센서 데이터를 이쪽으로 보내."
sock.sendto(b"HELLO", (PICO_IP, PICO_PORT))
print("Sent HELLO to Pico")


# ------------------------------------------------------------
# Pico가 주기적으로 보내는 ADC 데이터 수신
# ------------------------------------------------------------

while True:
    try:
        data, addr = sock.recvfrom(1024)

        text = data.decode().strip()

        # Pico가 처음 HELLO에 대해 보내는 응답
        if text == "PICO_READY":
            print("Pico is ready")
            continue

        # Pico가 보내는 ADC 데이터 형식:
        #   t_ms,raw,voltage
        #
        # 예:
        #   123456,32768,1.650
        parts = text.split(",")

        if len(parts) == 3:
            t_ms = int(parts[0])
            raw = int(parts[1])
            voltage = float(parts[2])

            print(f"t={t_ms:8d} ms | ADC2={raw:5d} | voltage={voltage:.3f} V")

        else:
            print("Unknown data:", text)

    except socket.timeout:
        # 일정 시간 동안 데이터가 안 오면 HELLO를 다시 보낸다.
        #
        # Pico가 리셋되었거나,
        # 노트북 프로그램을 다시 실행했거나,
        # Wi-Fi가 잠깐 끊겼을 때 유용하다.
        print("No data... send HELLO again")
        sock.sendto(b"HELLO", (PICO_IP, PICO_PORT))

    except KeyboardInterrupt:
        print("Stopped")
        break


sock.close()
