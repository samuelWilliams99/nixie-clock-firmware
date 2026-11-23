from machine import RTC

from time import gmtime, mktime, time_ns
import ntptime
import _thread

class NetworkClock:
  time_ready = False
  ready_handler = None

  def __init__(self, network_manager, timer_manager, ready_handler):
    self.ready_handler = ready_handler
    self.network_manager = network_manager
    self.timer_manager = timer_manager
    network_manager.add_handler(self.network_connected)

  def network_connected(self):
    self.update_time_after(1)

  # Delay in ms
  def update_time_after(self, delay):
    print(f"Next time update in {delay} seconds")
    def callback():
      _thread.start_new_thread(self.update_time, [])
    self.timer_manager.start_timer(name="network-clock-update", delay=delay, callback=callback)

  # Tries to get time with exponential falloff, starting at 1s, maxing at 60s
  def update_time(self, delay=1):
    if not self.network_manager.check_wifi(): return
    time = None
    try:
      time = ntptime.time()
    except Exception as e:
      print("failed time check: " + str(e))
    if time != None:
      self.update_time_with(time)
    else:
      def falloff_callback():
        _thread.start_new_thread(self.update_time, [min(delay * 2, 60)])
      self.timer_manager.start_timer(name="network-clock-update", delay=delay, callback=falloff_callback)

  def update_time_with(self, gmt_unix):
    gmt_tuple = gmtime(gmt_unix)
    bst_start_unix = self.get_last_sunday_of_month(gmt_tuple[0], 3)
    bst_end_unix = self.get_last_sunday_of_month(gmt_tuple[0], 10)

    uk_unix = gmt_unix
    if gmt_unix >= bst_start_unix and gmt_unix <= bst_end_unix:
      uk_unix = gmt_unix + 3600 # BST is GMT + 1

    uk_tuple = gmtime(uk_unix)

    pre_update_time = time_ns()
    RTC().datetime((uk_tuple[0], uk_tuple[1], uk_tuple[2], uk_tuple[6] + 1, uk_tuple[3], uk_tuple[4], uk_tuple[5], 0))
    post_update_time = time_ns()
    self.timer_manager.time_skip(post_update_time - pre_update_time)
    self.time_ready = True

    if self.ready_handler != None:
      self.ready_handler()
    self.ready_handler = None

    # Update the time at 1:05am each morning
    # First find out tomorrows tuple, to account for month/year rollover
    tmr_tuple = gmtime(uk_unix + 24 * 60 * 60)
    next_update_unix = mktime((tmr_tuple[0], tmr_tuple[1], tmr_tuple[2], 1, 5, 0, 0, 0))
    delay_to_update_seconds = next_update_unix - uk_unix
    self.update_time_after(delay_to_update_seconds)

  # Gets timestamp of 1am last sunday of a given month/year
  # (assumes the month has 31 days because I'm lazy and that's all we need)
  def get_last_sunday_of_month(self, year, month):
    last_of_month_tuple = gmtime(mktime((year, month, 31, 1, 0, 0, 0, 0)))
    # Day of week is 0-6 for Mon to Sun, we want to subtract to last Sunday
    # so we add 1 one mod by 7, then subtract that from current day
    # Sunday would give 0, Saturday would give 6 (so go back to previous sunday), etc.
    day_offset = (last_of_month_tuple[6] + 1) % 7
    return mktime((year, month, 31 - day_offset, 1, 0, 0, 0, 0))