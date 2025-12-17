from ria_wifi import RiaWiFi, WiFiError

wifi = RiaWiFi()

try:
    net = wifi.connect("Ria2G", "730124go", precheck=True)
    print("Connected SSID:", wifi.ssid)
    print("IP:", wifi.ip)

except WiFiError as e:
    print("WiFiError:", e)
