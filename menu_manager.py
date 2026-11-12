from machine import Timer, RTC
from display import Display
from button_manager import ButtonManager
from network_clock import NetworkClock
from time import time_ns, sleep
import random

class MenuManager:
  menus = []
  active_menu = None
  menu_change_anim_state = 0
  next_menu = None
  fps = 24
  timer = Timer(-1)

  def __init__(self):
    self.display = Display()
    self.button_manager = ButtonManager()
    def handler(button, is_pressed):
      if not self.active_menu or self.is_in_anim(): return
      self.active_menu.handle_button(button, is_pressed)
    self.button_manager.set_handler(handler)
    def callback(_t):
      self.render()
    self.timer.init(period=1000 // self.fps , callback=callback)

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
    self.display.enable()

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
    self.network_clock = NetworkClock()

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
    if is_pressed and button == 5: self.manager.display.enable()
    if is_pressed and button == 4: self.manager.display.disable()
    if is_pressed and (button == 2 or button == 3): self.manager.set_menu("disco")
    if is_pressed and button == 0: self.manager.set_menu("date")

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
    pass

class Disco(Menu):
  menu_name = "disco"

  def __init__(self):
    self.network_clock = NetworkClock()


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

def main():
  # Delay startup in case we hit an error state, give time for upload before throwing, as thrown errors interrupt upload
  sleep(5)
  menu_manager = MenuManager()
  menu_manager.register_menu(Clock())
  menu_manager.register_menu(Date())
  menu_manager.register_menu(Disco())
  menu_manager.initialize("clock")
