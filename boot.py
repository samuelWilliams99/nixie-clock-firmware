import network
import main
sta_if = network.WLAN(network.WLAN.IF_STA)
if not sta_if.isconnected():
    print('connecting to network...')
    sta_if.active(True)
    sta_if.connect('ICO-2D5F85', '3Swufigorrus')
    while not sta_if.isconnected():
        pass
print('network config:', sta_if.ipconfig('addr4'))

main.main()