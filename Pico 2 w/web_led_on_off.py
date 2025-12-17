from ria_wifi import RiaWiFi, WiFiError
import socket
from machine import Pin

# ---------- 설정 ----------
SSID = "Ria2G"
PW   = "730124go"
PORT = 80  # 필요하면 8080으로 변경

# ---------- LED ----------
try:
    led = Pin("LED", Pin.OUT)   # Pico W / Pico 2 W
except Exception:
    led = Pin(25, Pin.OUT)      # fallback
led.off()

def load_template(path="index.html"):
    with open(path, "r") as f:
        return f.read()

def render(template, ip, led_on):
    page = template
    page = page.replace("__IP__", ip)
    page = page.replace("__LED__", "ON" if led_on else "OFF")
    return page

def send(cl, status_line, headers, body=""):
    cl.send(status_line + "\r\n")
    for h in headers:
        cl.send(h + "\r\n")
    cl.send("\r\n")
    if body:
        cl.send(body)

def redirect(cl, location="/"):
    send(cl, "HTTP/1.1 302 Found", [f"Location: {location}", "Connection: close"])

def serve_forever(ip, port=80):
    template = load_template("index.html")

    addr = socket.getaddrinfo("0.0.0.0", port)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(1)

    print("Open:", "http://%s:%d/" % (ip, port))

    while True:
        cl, remote = s.accept()
        try:
            req = cl.recv(1024)
            if not req:
                cl.close()
                continue

            first = req.split(b"\r\n", 1)[0]
            parts = first.split()
            path = parts[1].decode() if len(parts) >= 2 else "/"

            if path == "/on":
                led.on()
                redirect(cl, "/")

            elif path == "/off":
                led.off()
                redirect(cl, "/")

            elif path == "/favicon.ico":
                send(cl, "HTTP/1.1 204 No Content", ["Connection: close"])

            else:
                body = render(template, ip, led.value() == 1)
                send(
                    cl,
                    "HTTP/1.1 200 OK",
                    ["Content-Type: text/html; charset=utf-8", "Connection: close"],
                    body
                )

        except Exception:
            try:
                send(cl, "HTTP/1.1 500 Internal Server Error", ["Connection: close"])
            except:
                pass
        finally:
            cl.close()

# ---------- 실행 ----------
wifi = RiaWiFi()

try:
    info = wifi.connect(SSID, PW)  # precheck 기본 True
    ip = info.ip
    print("Connected IP:", ip)
    serve_forever(ip, PORT)

except WiFiError as e:
    print("WiFiError:", e)
except Exception as e:
    print("Unexpected:", e)

