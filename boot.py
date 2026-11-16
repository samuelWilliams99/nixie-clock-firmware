import network
from menu_manager import main
from wifi import known_networks

sta_if = network.WLAN(network.WLAN.IF_STA)
print("Scanning for known networks...")
sta_if.active(True)
networks = sta_if.scan()
found = False
for n in networks:
  network_name = n[0].decode('utf-8')
  if network_name in known_networks:
    found = True
    print("Found network " + network_name + ", connecting...")
    sta_if.connect(network_name, known_networks[network_name])
    break
if not found:
  print("Failed to find known network, clock will start with unknown time")

main(found)