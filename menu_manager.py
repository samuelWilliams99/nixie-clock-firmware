from machine import Timer, RTC
from display import Display
from button_manager import ButtonManager
from network_clock import NetworkClock
from time import localtime

class MenuManager:
  menus = []
  active_menu = None
  menu_change_anim_state = 0
  menu_change_anim_frame_counter = 0
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
    self.menus.push(menu)

  def is_in_anim(self):
    return self.next_menu or self.menu_change_anim_state > 0

  def to_brightness(self, is_on):
    return 0x7FFF if is_on else 0

  def render(self):
    if self.next_menu:
      self.menu_change_anim_frame_counter += 1
      if self.menu_change_anim_frame_counter == 2:
        self.menu_change_anim_frame_counter = 0
        self.menu_change_anim_state += 1
        if self.menu_change_anim_state == 8:
          self.active_menu = self.next_menu
          self.next_menu = None
    elif self.menu_change_anim_state > 0:
      self.menu_change_anim_frame_counter += 1
      if self.menu_change_anim_frame_counter == 2:
        self.menu_change_anim_frame_counter = 0
        self.menu_change_anim_state -= 1
    (digits, commas) = self.get_render_data()
    for i in range(6):
      digit = digits[i] or 0
      self.display.set_digit(i, digit, self.to_brightness(digits[i]))
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
  last_button = 0

  def __init__(self):
    self.network_clock = NetworkClock()

  # take a number and render it to a 2 digit array, with padding/truncation
  def render_to_digit_array(self, num):
    [(num // 10) % 10, num % 10]

  def start(self):
    pass

  def stop(self):
    pass
  
  def render(self):
    t = self.rtc.now()
    hour = t[3]
    min = t[4]
    sec = t[5]
    # TODO, replace last_button with hour
    digits = self.render_to_digit_array(self.last_button) + self.render_to_digit_array(min) + self.render_to_digit_array(sec)
    # Work out how to do commas, needs to be synced to localtime annoyingly
    # t[6] might be accurate micoseconds, in which case:
    comma_num = min(t[6] // (1000000 // 12), 11)
    commas = [False] * 12
    commas[comma_num] = True
    return (digits, commas)

  def handle_button(self, button, is_pressed):
    if not is_pressed: return
    self.last_button = button

def main():
  menu_manager = MenuManager()
  menu_manager.register(Clock())
  menu_manager.initialize()
