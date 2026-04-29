# pc_adc2_live_plot.py

import socket
import time
from collections import deque

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation


# ------------------------------------------------------------
# Pico 2 W UDP 설정
# ------------------------------------------------------------

# Pico 2 W가 AP 모드일 때 보통 자기 IP는 192.168.4.1이다.
PICO_IP = "192.168.4.1"

# Pico 코드에서 UDP 수신용으로 사용한 포트
PICO_PORT = 5005

# 노트북이 UDP 데이터를 받을 포트
# Pico는 노트북이 HELLO를 보낸 포트로 데이터를 다시 보낸다.
LOCAL_PORT = 6000


# ------------------------------------------------------------
# 그래프 설정
# ------------------------------------------------------------

# 화면에 최근 몇 초 동안의 데이터만 보여줄지 설정
WINDOW_SEC = 10

# 너무 많은 데이터를 계속 쌓지 않도록 최대 저장 개수 설정
MAX_POINTS = 1000


# ------------------------------------------------------------
# UDP 소켓 생성
# ------------------------------------------------------------

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# 노트북의 UDP 수신 포트를 고정한다.
sock.bind(("", LOCAL_PORT))

# 그래프가 멈추지 않도록 non-blocking 모드로 설정한다.
# 데이터가 없어도 recvfrom()에서 기다리지 않는다.
sock.setblocking(False)


# ------------------------------------------------------------
# Pico에게 HELLO 전송
# ------------------------------------------------------------

def send_hello():
    """
    Pico에게 HELLO를 보낸다.

    의미:
        "Pico야, 내 IP와 포트는 여기야.
         앞으로 ADC 데이터를 이쪽으로 보내."
    """
    sock.sendto(b"HELLO", (PICO_IP, PICO_PORT))


print("ADC2 live plot started")
print("Local UDP port:", LOCAL_PORT)
print("Pico target:", PICO_IP, PICO_PORT)

send_hello()
print("Sent HELLO to Pico")


# ------------------------------------------------------------
# 데이터 저장용 버퍼
# ------------------------------------------------------------

# x축: Pico 기준 시간, 단위 초
time_data = deque(maxlen=MAX_POINTS)

# y축: 전압값
voltage_data = deque(maxlen=MAX_POINTS)

# 참고용 ADC raw 값
raw_data = deque(maxlen=MAX_POINTS)

# 첫 번째로 받은 Pico 시간
# 그래프 x축을 0초부터 시작시키기 위해 사용한다.
first_pico_time_ms = None

# 마지막으로 데이터를 받은 PC 시간
last_receive_time = time.time()

# 마지막으로 HELLO를 보낸 PC 시간
last_hello_time = time.time()


# ------------------------------------------------------------
# Matplotlib 그래프 준비
# ------------------------------------------------------------

fig, ax = plt.subplots()

line, = ax.plot([], [], label="ADC2 Voltage")

ax.set_title("Pico 2 W ADC2 Real-time UDP Monitor")
ax.set_xlabel("Time from first sample [s]")
ax.set_ylabel("Voltage [V]")

# 가변저항을 0~3.3V 범위에서 사용한다고 가정
ax.set_ylim(-0.1, 3.4)

ax.grid(True)
ax.legend(loc="upper right")

# 그래프 안에 현재 값 표시용 텍스트
info_text = ax.text(
    0.02, 0.95,
    "",
    transform=ax.transAxes,
    verticalalignment="top"
)


# ------------------------------------------------------------
# UDP 데이터 수신 함수
# ------------------------------------------------------------

def receive_udp_data():
    """
    현재 소켓에 들어와 있는 UDP 데이터를 모두 읽는다.

    Pico가 보내는 데이터 예:
        123450,32768,1.650

    의미:
        t_ms = 123450 ms
        raw = 32768
        voltage = 1.650 V
    """
    global first_pico_time_ms
    global last_receive_time

    received_any = False

    while True:
        try:
            data, addr = sock.recvfrom(1024)

        except BlockingIOError:
            # 더 이상 읽을 UDP 데이터가 없다는 뜻
            break

        except OSError:
            # MicroPython/Windows 환경에 따라 데이터가 없을 때 OSError가 날 수도 있어 대비
            break

        text = data.decode().strip()

        # Pico가 HELLO에 대해 보내는 준비 완료 메시지
        if text == "PICO_READY":
            print("Pico is ready")
            last_receive_time = time.time()
            received_any = True
            continue

        parts = text.split(",")

        if len(parts) != 3:
            print("Unknown data:", text)
            continue

        try:
            t_ms = int(parts[0])
            raw = int(parts[1])
            voltage = float(parts[2])

        except ValueError:
            print("Parse error:", text)
            continue

        # 첫 샘플 시간을 기준으로 그래프 x축을 0초부터 시작
        if first_pico_time_ms is None:
            first_pico_time_ms = t_ms

        t_sec = (t_ms - first_pico_time_ms) / 1000.0

        time_data.append(t_sec)
        raw_data.append(raw)
        voltage_data.append(voltage)

        last_receive_time = time.time()
        received_any = True

    return received_any


# ------------------------------------------------------------
# 그래프 업데이트 함수
# ------------------------------------------------------------

def update_graph(frame):
    global last_hello_time

    # 1. UDP 데이터 수신
    receive_udp_data()

    # 2. 일정 시간 동안 데이터가 없으면 HELLO를 다시 보낸다.
    #    Pico가 리셋되었거나 노트북 프로그램을 다시 시작했을 때 유용하다.
    now = time.time()

    if now - last_receive_time > 2.0:
        if now - last_hello_time > 1.0:
            send_hello()
            last_hello_time = now
            print("No data... sent HELLO again")

    # 3. 그래프 데이터 갱신
    if len(time_data) > 0:
        line.set_data(time_data, voltage_data)

        latest_t = time_data[-1]
        latest_raw = raw_data[-1]
        latest_voltage = voltage_data[-1]

        # 최근 WINDOW_SEC 초만 보이도록 x축 이동
        if latest_t < WINDOW_SEC:
            ax.set_xlim(0, WINDOW_SEC)
        else:
            ax.set_xlim(latest_t - WINDOW_SEC, latest_t)

        info_text.set_text(
            f"ADC2 raw: {latest_raw}\n"
            f"Voltage: {latest_voltage:.3f} V\n"
            f"Samples: {len(time_data)}"
        )

    return line, info_text


# ------------------------------------------------------------
# 애니메이션 실행
# ------------------------------------------------------------

# interval=50:
#   50ms마다 그래프 업데이트 시도
#   Pico가 50ms마다 데이터를 보내면 거의 같은 주기로 화면이 갱신된다.
ani = FuncAnimation(
    fig,
    update_graph,
    interval=50,
    blit=False
)

try:
    plt.show()

finally:
    sock.close()
    print("Socket closed")
