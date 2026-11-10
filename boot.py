import network
import main
from wifi import wifi_name, wifi_password
sta_if = network.WLAN(network.WLAN.IF_STA)
if not sta_if.isconnected():
    print('connecting to network...')
    sta_if.active(True)
    sta_if.connect(wifi_name, wifi_password)
    while not sta_if.isconnected():
        pass
print('network config:', sta_if.ipconfig('addr4'))

main.main()