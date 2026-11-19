from machine import Timer
import _thread
import network
from wifi import known_networks

class NetworkManager:
  sta_if = network.WLAN(network.WLAN.IF_STA)
  handlers = []
  timer = Timer(-1)

  def __init__(self):
    self.sta_if.active(True)

  def add_handler(self, handler):
    self.handlers.append(handler)

  def check_wifi(self):
    if self.sta_if.isconnected(): return True
    if self.sta_if.status() == network.STAT_CONNECTING:
      return False
    else:
      self.connect()
      return False

  def isconnected(self):
    return self.sta_if.isconnected()

  def select_network(self):
    networks = self.sta_if.scan()
    for n in networks:
      network_name = n[0].decode('utf-8')
      if network_name in known_networks:
        return network_name
    return None

  def connect(self):
    _thread.start_new_thread(self.connect_blocking, [])

  def connect_blocking(self):
    print("Scanning for known networks...")
    network_name = self.select_network()
    if network_name != None:
      print("Found network " + network_name + ", connecting...")
      self.sta_if.connect(network_name, known_networks[network_name])
      def connecting_callback(t):
        status = self.sta_if.status()
        # Micropython is missing this status code for some reason
        STAT_NOIP = 2
        if self.sta_if.isconnected():
          t.deinit()
          print("Connected successfully")
          for handler in self.handlers:
            handler()
        elif status not in [network.STAT_CONNECTING, STAT_NOIP, network.STAT_NO_AP_FOUND]:
          print(f"Connection failed {status}, retrying...")
          t.deinit()
          self.connect()
        else:
          print("Waiting for connection...")
      self.timer.init(period=1000, callback=connecting_callback)
    else:
      print("Failed to find known network, retrying in 60s")
      def connect_callback(t):
        t.deinit()
        self.connect()
      self.timer.init(mode=Timer.ONE_SHOT, period=60000, callback=connect_callback)
