from time import time_ns

class TimerManager:
  timers = {}

  # Takes delay in seconds
  def start_timer(self, name, delay, callback):
    next_trigger = time_ns() + delay * 1000000000
    print(f"added timer for {name} at {next_trigger}")
    self.timers[name] = Timer(callback, next_trigger)

  # Account for time skipping when network clock updates RTC
  def time_skip(self, amount_ns):
    for timer in self.timers.values():
      timer.next_trigger += amount_ns

  def tick(self):
    time = time_ns()
    for name, timer in self.timers.copy().items():
      if timer.next_trigger < time:
        print(f"Running timer for {name}")
        del self.timers[name]
        timer.callback()

class Timer:
  next_trigger = None
  callback = None

  def __init__(self, callback, next_trigger):
    self.callback = callback
    self.next_trigger = next_trigger
