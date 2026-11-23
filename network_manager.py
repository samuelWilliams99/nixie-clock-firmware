import _thread
import network
from wifi import known_networks

class NetworkManager:
  sta_if = network.WLAN(network.WLAN.IF_STA)
  handlers = []

  def __init__(self, timer_manager):
    self.timer_manager = timer_manager
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
      def connecting_callback():
        status = self.sta_if.status()
        # Micropython is missing this status code for some reason
        STAT_NOIP = 2
        if self.sta_if.isconnected():
          print("Connected successfully")
          for handler in self.handlers:
            handler()
        elif status not in [network.STAT_CONNECTING, STAT_NOIP, network.STAT_NO_AP_FOUND]:
          print(f"Connection failed {status}, retrying...")
          self.connect()
        else:
          print("Waiting for connection...")
          start_timer()
      def start_timer():
        self.timer_manager.start_timer(name="network-connection", delay=1, callback=connecting_callback)
      start_timer()
    else:
      print("Failed to find known network, retrying in 10s")
      self.timer_manager.start_timer(name="network-connection", delay=10, callback=self.connect)
