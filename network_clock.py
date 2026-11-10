from machine import RTC, Timer

from time import gmtime, mktime, sleep
import ntptime

class NetworkClock:
  time_ready = False
  # Use this for signalling somehow, maybe keep the bottom bar full
  failing_ntp_lookup = False
  # Virtual timer is fine
  timer = Timer(-1)

  # Blocking constructor to setup time
  def __init__(self):
    self.update_time()

  # Delay in ms
  def update_time_after(self, delay):
    def callback(_t):
      self.update_time()
    self.timer.init(mode=Timer.ONE_SHOT, period=delay, callback=callback)

  # Tries to get time with exponential falloff, starting at 1s, maxing at 60s
  def ntp_time_falloff(self):
    delay = 1
    while True:
      try:
        time = ntptime.time()
        self.failing_ntp_lookup = False
        return time
      except:
        pass
      self.failing_ntp_lookup = True
      delay = min(delay * 2, 60)
      sleep(delay)

  def update_time(self):
    gmt_unix = self.ntp_time_falloff()

    gmt_tuple = gmtime(gmt_unix)
    bst_start_unix = self.get_last_sunday_of_month(gmt_tuple[0], 3)
    bst_end_unix = self.get_last_sunday_of_month(gmt_tuple[0], 10)

    uk_unix = gmt_unix
    if gmt_unix >= bst_start_unix and gmt_unix <= bst_end_unix:
      uk_unix = gmt_unix + 3600 # BST is GMT + 1

    uk_tuple = gmtime(uk_unix)

    RTC().datetime((uk_tuple[0], uk_tuple[1], uk_tuple[2], uk_tuple[6] + 1, uk_tuple[3], uk_tuple[4], uk_tuple[5], 0))
    self.time_ready = True

    # Update the time at 1:05am each morning
    # First find out tomorrows tuple, to account for month/year rollover
    tmr_tuple = gmtime(uk_unix + 24 * 60 * 60)
    next_update_unix = mktime((tmr_tuple[0], tmr_tuple[1], tmr_tuple[2], 1, 5, 0, 0, 0))
    delay_to_update_seconds = next_update_unix - uk_unix
    self.update_time_after(delay_to_update_seconds * 1000)

  # Gets timestamp of 1am last sunday of a given month/year
  # (assumes the month has 31 days because I'm lazy and that's all we need)
  def get_last_sunday_of_month(self, year, month):
    last_of_month_tuple = gmtime(mktime((year, month, 31, 1, 0, 0, 0, 0)))
    # Day of week is 0-6 for Mon to Sun, we want to subtract to last Sunday
    # so we add 1 one mod by 7, then subtract that from current day
    # Sunday would give 0, Saturday would give 6 (so go back to previous sunday), etc.
    day_offset = (last_of_month_tuple[6] + 1) % 7
    mktime((year, month, 31 - day_offset, 1, 0, 0, 0, 0))