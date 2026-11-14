from machine import Timer, RTC
from display import Display
from button_manager import ButtonManager
from network_clock import NetworkClock
from time import time_ns, sleep, localtime, mktime
import random

class MenuManager:
  menus = []
  active_menu = None
  menu_change_anim_state = 0
  next_menu = None
  fps = 24
  render_timer = Timer(-1)
  display_on_off_timer = Timer(-1)
  off_hour = 1
  on_hour = 9

  def set_next_on_off_timer(self, should_change_state = True):
    t = localtime()
    current_epoch = mktime(t)

    if self.on_hour > self.off_hour:
      # The "off" time is in the same day
      should_be_on = not (self.off_hour <= t[3] < self.on_hour)
    else:
      # The "On" time is in the same day
      should_be_on = self.on_hour <= t[3] < self.off_hour

    if should_be_on:
      next_hour = self.off_hour
      if should_change_state: self.display.enable()
    else:
      next_hour = self.on_hour
      if should_change_state: self.display.disable()
      
    next_epoch = mktime((t[0], t[1], t[2], next_hour, 5, 0, 0, 0))
    # If its in the past then switch to tomorrow
    if next_epoch < current_epoch:
      next_epoch += 24 * 60 * 60

    delay = next_epoch - current_epoch
    def callback():
      self.set_next_on_off_timer()
    self.display_on_off_timer.init(mode=Timer.ONE_SHOT, period=1000 * delay, callback=callback)

  def __init__(self):
    self.display = Display()
    self.button_manager = ButtonManager()
    def clock_callback():
      self.set_next_on_off_timer()
    self.network_clock = NetworkClock(clock_callback)

    def handler(button, is_pressed):
      if not self.active_menu or self.is_in_anim(): return
      self.active_menu.handle_button(button, is_pressed)
    self.button_manager.set_handler(handler)
    def render_callback(_t):
      self.render()
    self.render_timer.init(period=1000 // self.fps , callback=render_callback)

  def register_menu(self, menu):
    self.menus.append(menu)

  def is_in_anim(self):
    return self.next_menu or self.menu_change_anim_state > 0

  def to_brightness(self, is_on):
    return 0x7FFF if is_on else 0

  def render(self):
    if self.next_menu:
      self.menu_change_anim_state += 1
      if self.menu_change_anim_state == 8:
        if self.active_menu != None: self.active_menu.stop()
        self.active_menu = self.next_menu
        self.active_menu.start(self)
        self.next_menu = None
    elif self.menu_change_anim_state > 0:
      self.menu_change_anim_state -= 1
    (digits, commas) = self.get_render_data()
    for i in range(6):
      digit = digits[i] or 0
      self.display.set_digit(i, digit, self.to_brightness(digits[i] != None))
      self.display.set_digit_commas(i, self.to_brightness(commas[i*2]), self.to_brightness(commas[(i*2) + 1]))

  def get_render_data(self):
    if not self.active_menu:
      return ([None] * 6, [False] * 12)
    (digits, commas) = self.active_menu.render()
    if self.next_menu:
      n = min(self.menu_change_anim_state, 6)
      return (([None] * n) + digits[n:], ([False] * (n*2)) + commas[(n*2):])
    elif self.menu_change_anim_state > 0:
      n = min(self.menu_change_anim_state, 6)
      return (digits[:(6-n)] + ([None] * n), commas[:((6-n)*2)] + ([False] * (n*2)))
    else:
      return (digits, commas)

  # Takes the menu name
  def set_menu(self, menu_name):
    if self.next_menu: return
    for menu in self.menus:
      if menu.menu_name == menu_name:
        self.next_menu = menu

  def initialize(self, first_menu_name):
    self.set_menu(first_menu_name)

class Menu:
  menu_name = "<default>"

  def start(self):
    pass

  def stop(self):
    pass

  def render(self):
    pass

  def handle_button(self, button, is_pressed):
    pass

class Clock(Menu):
  menu_name = "clock"
  rtc = RTC()

  def __init__(self):
    pass

  # take a number and render it to a 2 digit array, with padding/truncation
  def render_to_digit_array(self, num):
    return [(num // 10) % 10, num % 10]

  def start(self, manager):
    self.manager = manager
    pass

  def stop(self):
    pass
  
  def render(self):
    t = self.rtc.datetime()
    hours = t[4]
    minutes = t[5]
    seconds = t[6]
    digits = self.render_to_digit_array(hours) + self.render_to_digit_array(minutes) + self.render_to_digit_array(seconds)
    ms = (time_ns() // 1000000) % 1000
    comma_num = min(ms // (1000 // 12), 11)
    commas = [False] * 12
    commas[comma_num] = True
    return (digits, commas)

  def handle_button(self, button, is_pressed):
    if not is_pressed: return
    if button == 0: self.manager.set_menu("date")
    if button == 2: self.manager.set_menu("disco")
    if button == 3: self.manager.set_menu("tubetest")
    if button == 4: self.manager.set_menu("setdisplayonoff")
    if button == 5: self.manager.display.set_enabled(not self.manager.display.enabled)

class Date(Menu):
  menu_name = "date"
  rtc = RTC()
  total_time_ms = 5000

  # take a number and render it to a 2 digit array, with padding/truncation
  def render_to_digit_array(self, num):
    return [(num // 10) % 10, num % 10]

  def time_ms(self): return time_ns() // 1000000

  def start(self, manager):
    self.manager = manager
    self.time_started_ms = self.time_ms()
    pass

  def stop(self):
    pass
  
  def render(self):
    t = self.rtc.datetime()
    day = t[2]
    month = t[1]
    year = t[0] - 2000
    digits = self.render_to_digit_array(day) + self.render_to_digit_array(month) + self.render_to_digit_array(year)
    remaining_ms = max(self.time_started_ms + self.total_time_ms - self.time_ms(), 0)

    if remaining_ms == 0: self.manager.set_menu("clock")
     
    comma_num = min(remaining_ms // (self.total_time_ms // 13), 12)
    commas = ([True] * comma_num) + ([False] * (12 - comma_num))
    return (digits, commas)

  def handle_button(self, button, is_pressed):
    if not is_pressed: return
    self.manager.set_menu("clock")

class Disco(Menu):
  menu_name = "disco"

  def __init__(self):
    pass

  def start(self, manager):
    self.manager = manager
    pass

  def stop(self):
    pass

  def rand_digit(self):
    return random.randint(0, 9)

  def rand_bool(self):
    return random.getrandbits(1) == 1
  
  def render(self):
    digits = [self.rand_digit(), self.rand_digit(), self.rand_digit(), self.rand_digit(), self.rand_digit(), self.rand_digit()]
    commas = [
      self.rand_bool(), self.rand_bool(), self.rand_bool(), self.rand_bool(), self.rand_bool(), self.rand_bool(),
      self.rand_bool(), self.rand_bool(), self.rand_bool(), self.rand_bool(), self.rand_bool(), self.rand_bool()
    ]
    return (digits, commas)

  def handle_button(self, button, is_pressed):
    if is_pressed: self.manager.set_menu("clock")

class TubeTest(Menu):
  menu_name = "tubetest"

  def start(self, manager):
    self.manager = manager
    self.digits = [0] * 6
    pass

  def stop(self):
    pass

  def render(self):
    return (self.digits, [True] * 12)

  def handle_button(self, button, is_pressed):
    if is_pressed:
      self.digits[button] = (self.digits[button] + 1) % 10
      self.last_button = button
      self.last_down = time_ns()
    else:
      if button == self.last_button and time_ns() - self.last_down > 1000000000:
        self.manager.set_menu("clock")

class SetDisplayOnOff(Menu):
  menu_name = "setdisplayonoff"

  def start(self, manager):
    self.manager = manager

  def render_to_digit_array(self, num):
    return [(num // 10) % 10, num % 10]

  def stop(self):
    pass

  def render(self):
    return (self.render_to_digit_array(self.manager.off_hour) + [None, None] + self.render_to_digit_array(self.manager.on_hour), ([False] * 6) + ([True] * 6))

  def handle_button(self, button, is_pressed):
    if not is_pressed: return
    if button == 2 or button == 3:
      self.manager.set_menu("clock")
      return
    if button == 0: self.manager.off_hour = (self.manager.off_hour - 1) % 24
    if button == 1: self.manager.off_hour = (self.manager.off_hour + 1) % 24
    if button == 4: self.manager.on_hour = (self.manager.on_hour - 1) % 24
    if button == 5: self.manager.on_hour = (self.manager.on_hour + 1) % 24
    self.manager.set_next_on_off_timer(should_change_state=False)

def main():
  # Delay startup in case we hit an error state, give time for upload before throwing, as thrown errors interrupt upload
  menu_manager = MenuManager()
  menu_manager.register_menu(Clock())
  menu_manager.register_menu(Date())
  menu_manager.register_menu(Disco())
  menu_manager.register_menu(TubeTest())
  menu_manager.register_menu(SetDisplayOnOff())
  menu_manager.initialize("clock")
