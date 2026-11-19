from machine import Timer, RTC
from display import Display
from button_manager import ButtonManager
from network_clock import NetworkClock
from weather_manager import WeatherManager
from network_manager import NetworkManager
from time import time_ns, localtime, mktime, ticks_ms
import random
import network
import gc
import math

class MenuManager:
  menus = []
  active_menu = None
  menu_change_anim_state = 0
  next_menu = None
  fps = 24
  render_timer = Timer(-1)

  def __init__(self):
    self.network_manager = NetworkManager()
    self.weather_manager = WeatherManager(self.network_manager)

  def register_menu(self, make_menu):
    menu = make_menu(self)
    self.menus.append(menu)

  def is_in_anim(self):
    return self.next_menu or self.menu_change_anim_state > 0

  def render(self):
    # Glow lasts 8 frames
    self.display.tick_update_glows(6)
    if self.next_menu:
      self.menu_change_anim_state += 1
      if self.menu_change_anim_state == 8:
        if self.active_menu != None: self.active_menu.stop()
        self.active_menu = self.next_menu
        self.active_menu.start()
        self.display.set_update_glow(self.active_menu.do_update_glow)
        self.next_menu = None
        if self.active_menu.skip_anim:
          self.menu_change_anim_state = 0
    elif self.menu_change_anim_state > 0:
      self.menu_change_anim_state -= 1
    (digits, commas) = self.get_render_data()
    for i in range(6):
      self.display.set_digit(i, digits[i])
      self.display.set_digit_commas(i, commas[i*2], commas[(i*2) + 1])

  def get_render_data(self):
    if not self.active_menu:
      # Loading menu, sliding dot means connecting to internet, alternating means getting time
      t = ticks_ms()
      n = t // 100
      if self.network_manager.isconnected():
        if n % 4 > 1:
          return ([None] * 6, [True, False] * 6)
        else:
          return ([None] * 6, [False, True] * 6)
      else:
        cs = [False] * 12
        cs[n % 12] = True
        return ([None] * 6, cs)
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
    if self.active_menu and self.active_menu.menu_name == menu_name: return
    for menu in self.menus:
      if menu.menu_name == menu_name:
        self.next_menu = menu
        if self.active_menu and self.active_menu.skip_anim:
          # One less than max since render will bump it up
          self.menu_change_anim_state = 7

  def initialize(self):
    self.display = Display()
    self.button_manager = ButtonManager()
    def clock_callback():
      for menu in self.menus:
        menu.clock_ready()
      self.weather_manager.clock_ready()

    self.network_clock = NetworkClock(self.network_manager, clock_callback)

    def handler(button, is_pressed):
      if not self.active_menu or self.is_in_anim(): return
      self.active_menu.handle_button(button, is_pressed)
    self.button_manager.set_handler(handler)
    def render_callback(_t):
      self.render()
    self.render_timer.init(period=1000 // self.fps , callback=render_callback)
    self.display.enable()
    self.network_manager.connect()

class Menu:
  menu_name = "<default>"
  do_update_glow = False
  no_render = ([None] * 6, [False] * 12)
  skip_anim = False

  def render_to_n_digit_array(self, num, n, right_align = False, pad_character = None):
    if num == 0:
      if right_align:
        return ([pad_character] * (n-1)) + [0]
      else:
        return [0] + ([pad_character] * (n-1))
    digit_count = math.floor(math.log10(num)) + 1
    digits = [pad_character] * n
    # goes right to left on the number
    for i in range(digit_count):
      digit = (num // math.floor(math.pow(10, i))) % 10
      right_digit_index = n - 1 if right_align else digit_count - 1
      digits[right_digit_index - i] = digit
    return digits

  def render_2_digit_0_padded(self, num):
    return self.render_to_n_digit_array(num, 2, right_align=True, pad_character=0)

  def start(self):
    pass

  def stop(self):
    pass

  def render(self):
    return self.no_render

  def handle_button(self, button, is_pressed):
    pass

  def clock_ready(self):
    pass

class Clock(Menu):
  menu_name = "clock"
  rtc = RTC()
  button_4_last_down = None
  button_5_last_down = None
  config_menus = ["brightness", "setdisplayonoff"]
  debug_menus = ["memory", "disco", "tubetest"]
  do_update_glow = True

  def __init__(self, manager):
    self.manager = manager

  def clock_ready(self):
    self.manager.set_menu(self.menu_name)

  def get_config_menu_n(self, t_ns):
    if self.button_4_last_down == None or t_ns - self.button_4_last_down <= 1000000000: return None
    return (((t_ns - self.button_4_last_down) // 1000000000) - 1) % len(self.config_menus)

  def get_debug_menu_n(self, t_ns):
    if self.button_5_last_down == None or t_ns - self.button_5_last_down <= 1000000000: return None
    return (((t_ns - self.button_5_last_down) // 1000000000) - 1) % len(self.debug_menus)
  
  def render(self):
    t_ns = time_ns()
    config_menu_n = self.get_config_menu_n(t_ns)
    if config_menu_n != None:
      commas = [False] * 12
      commas[config_menu_n * 2] = True
      commas[(config_menu_n * 2) + 1] = True
      return ([None] * 6, commas)

    debug_menu_n = self.get_debug_menu_n(t_ns)
    if debug_menu_n != None:
      commas = [False] * 12
      commas[debug_menu_n * 2] = True
      commas[(debug_menu_n * 2) + 1] = True
      return ([None] * 6, commas)

    t = self.rtc.datetime()
    hours = t[4]
    minutes = t[5]
    seconds = t[6]
    digits = self.render_2_digit_0_padded(hours) + self.render_2_digit_0_padded(minutes) + self.render_2_digit_0_padded(seconds)
    ms = (t_ns // 1000000) % 1000
    comma_num = min(ms // (1000 // 12), 11)
    commas = [False] * 12
    commas[comma_num] = True
    return (digits, commas)

  def handle_button(self, button, is_pressed):
    if is_pressed and button == 0: self.manager.set_menu("date")
    if is_pressed and button == 1: self.manager.set_menu("temperature")
    if is_pressed and button == 2: self.manager.set_menu("humidity")
    if is_pressed and button == 3: self.manager.set_menu("rain_probability")
    if button == 4:
      if is_pressed:
        self.button_4_last_down = time_ns()
      else:
        menu_n = self.get_config_menu_n(time_ns())
        if menu_n == None:
          self.manager.display.pulse_glow()
        else:
          self.manager.set_menu(self.config_menus[menu_n])
        self.button_4_last_down = None

    if button == 5:
      if is_pressed:
        self.button_5_last_down = time_ns()
      else:
        menu_n = self.get_debug_menu_n(time_ns())
        if menu_n == None:
          if self.manager.active_menu.menu_name == "off":
            self.manager.set_menu("clock")
          else:
            self.manager.set_menu("off")
        else:
          self.manager.set_menu(self.debug_menus[menu_n])
        self.button_5_last_down = None

class Date(Menu):
  menu_name = "date"
  rtc = RTC()
  total_time_ms = 5000
  do_update_glow = True

  def time_ms(self): return time_ns() // 1000000

  def __init__(self, manager):
    self.manager = manager

  def start(self):
    self.time_started_ms = self.time_ms()
    pass
  
  def render(self):
    t = self.rtc.datetime()
    day = t[2]
    month = t[1]
    year = t[0] - 2000
    day_of_week = t[3]
    digits = self.render_2_digit_0_padded(day) + self.render_2_digit_0_padded(month) + self.render_2_digit_0_padded(year)

    if self.time_ms() - self.time_started_ms > self.total_time_ms:
      self.manager.set_menu("clock")

    commas = [False] * 12
    if day_of_week < 5:
      # Week day gets 2 lights
      commas[day_of_week * 2] = True
      commas[(day_of_week * 2) + 1] = True
    else:
      # Weekend gets one
      commas[day_of_week + 5] = True
    
    return (digits, commas)

  def handle_button(self, button, is_pressed):
    if not is_pressed: return
    self.manager.set_menu("clock")

class Disco(Menu):
  menu_name = "disco"

  def __init__(self, manager):
    self.manager = manager

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
  do_update_glow = True

  def __init__(self, manager):
    self.manager = manager

  def start(self):
    self.digits = [0] * 6
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

class Memory(Menu):
  menu_name = "memory"

  def __init__(self, manager):
    self.manager = manager

  def render(self):
    allocated_memory = gc.mem_alloc()
    comma_count = min((allocated_memory * 12) // 446656, 12)
    commas = ([True] * comma_count) + ([False] * (12 - comma_count))
    return (self.render_to_n_digit_array(allocated_memory, 6), commas)

  def handle_button(self, button, is_pressed):
    if is_pressed: self.manager.set_menu("clock")

class SetDisplayOnOff(Menu):
  menu_name = "setdisplayonoff"
  display_on_off_timer = Timer(-1)
  off_hour = 1
  on_hour = 9
  on_off_hour_filename = "on_off_times.txt"
  do_update_glow = True

  def __init__(self, manager):
    self.manager = manager

  # No-op if file no exist
  def read_on_off_hour(self):
    try:
      f = open(self.on_off_hour_filename)
      content = f.read()
      f.close()
      contents = content.split("\n")
      self.off_hour = int(contents[0])
      self.on_hour = int(contents[1])
    except:
      pass

  def write_on_off_hour(self):
    content = str(self.off_hour) + "\n" + str(self.on_hour)
    f = open(self.on_off_hour_filename, "w")
    f.write(content)
    f.close()

  def start(self):
    self.read_on_off_hour()

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
      print("turn on")
      if should_change_state:
        if not self.manager.active_menu or self.manager.active_menu.menu_name == "off": self.manager.set_menu("clock")
    else:
      next_hour = self.on_hour
      print("turn off")
      if should_change_state: self.manager.set_menu("off")
      
    next_epoch = mktime((t[0], t[1], t[2], next_hour, 0, 30, 0, 0))
    # If its in the past then switch to tomorrow
    if next_epoch < current_epoch:
      next_epoch += 24 * 60 * 60

    delay = next_epoch - current_epoch
    print(f"Next on-off update in {delay} seconds")
    def callback(t):
      t.deinit()
      self.set_next_on_off_timer()
    self.display_on_off_timer.init(mode=Timer.ONE_SHOT, period=1000 * delay, callback=callback)

  def clock_ready(self):
    self.set_next_on_off_timer()

  def render(self):
    return (self.render_2_digit_0_padded(self.off_hour) + [None, None] + self.render_2_digit_0_padded(self.on_hour), ([False] * 6) + ([True] * 6))

  def handle_button(self, button, is_pressed):
    if not is_pressed: return
    if button == 2 or button == 3:
      self.manager.set_menu("clock")
      return
    if button == 0: self.off_hour = (self.off_hour - 1) % 24
    if button == 1: self.off_hour = (self.off_hour + 1) % 24
    if button == 4: self.on_hour = (self.on_hour - 1) % 24
    if button == 5: self.on_hour = (self.on_hour + 1) % 24
    self.write_on_off_hour()
    self.set_next_on_off_timer(should_change_state=False)

class Brightness(Menu):
  menu_name = "brightness"
  do_update_glow = True

  def __init__(self, manager):
    self.manager = manager

  def render(self):
    return (
      self.render_2_digit_0_padded(self.manager.display.normal_brightness) + [None, None] + self.render_2_digit_0_padded(self.manager.display.glow_brightness),
      ([False] * 6) + ([True] * 6)
    )

  def handle_button(self, button, is_pressed):
    if not is_pressed: return
    if button == 2 or button == 3:
      self.manager.set_menu("clock")
      return
    if button == 0: self.manager.display.set_normal_brightness((self.manager.display.normal_brightness - 1) % 11)
    if button == 1: self.manager.display.set_normal_brightness((self.manager.display.normal_brightness + 1) % 11)
    if button == 4: self.manager.display.set_glow_brightness((self.manager.display.glow_brightness - 1) % 11)
    if button == 5: self.manager.display.set_glow_brightness((self.manager.display.glow_brightness + 1) % 11)

class GenericWeather(Menu):
  do_update_glow = True
  total_time_ms = 5000

  def __init__(self, manager):
    self.manager = manager
    self.weather_manager = manager.weather_manager

  def time_ms(self): return time_ns() // 1000000

  def start(self):
    self.time_started_ms = self.time_ms()

  def get_min(self):
    pass

  def get_current(self):
    pass

  def get_max(self):
    pass

  def render(self):
    if not self.weather_manager.ready:
      # Don't tick down if the weather isn't ready yet
      self.time_started_ms = self.time_ms()
      t = ticks_ms()
      n = t // 200
      if n % 2 == 0:
        return ([None] * 6, [True, False] * 6)
      else:
        return ([None] * 6, [False, True] * 6)

    if self.time_ms() - self.time_started_ms > self.total_time_ms:
      self.manager.set_menu("clock")

    (min_digits, min_commas) = self.render_value(self.get_min())
    (current_digits, current_commas) = self.render_value(self.get_current())
    (max_digits, max_commas) = self.render_value(self.get_max())
    return (min_digits + current_digits + max_digits, min_commas + current_commas + max_commas)

  def render_value(self, value):
    clamped = min(abs(value), 99)
    digits = self.render_to_n_digit_array(clamped, 2)
    if value == 100:
      commas = [True] * 4
    elif value < 0:
      commas = [True, True, False, False]
    else:
      commas = [False] * 4

    return (digits, commas)

  def handle_button(self, button, is_pressed):
    if is_pressed: self.manager.set_menu("clock")

class Temperature(GenericWeather):
  menu_name = "temperature"
  def get_min(self):
    return self.weather_manager.min_temperature

  def get_current(self):
    return self.weather_manager.current_temperature

  def get_max(self):
    return self.weather_manager.max_temperature

class Humidity(GenericWeather):
  menu_name = "humidity"
  def get_min(self):
    return self.weather_manager.min_humidity

  def get_current(self):
    return self.weather_manager.current_humidity

  def get_max(self):
    return self.weather_manager.max_humidity

class RainProbability(GenericWeather):
  menu_name = "rain_probability"
  def get_min(self):
    return self.weather_manager.min_rain_probability

  def get_current(self):
    return self.weather_manager.current_rain_probability

  def get_max(self):
    return self.weather_manager.max_rain_probability

class Off(Menu):
  menu_name = "off"
  skip_anim = True
  def __init__(self, manager):
    self.manager = manager

  def start(self):
    self.manager.display.disable()

  def stop(self):
    self.manager.display.enable()

  def handle_button(self, button, is_pressed):
    if is_pressed: self.manager.set_menu("clock")

def main():
  # Delay startup in case we hit an error state, give time for upload before throwing, as thrown errors interrupt upload
  menu_manager = MenuManager()
  menu_manager.register_menu(Clock)
  menu_manager.register_menu(Date)
  menu_manager.register_menu(Disco)
  menu_manager.register_menu(TubeTest)
  menu_manager.register_menu(SetDisplayOnOff)
  menu_manager.register_menu(Memory)
  menu_manager.register_menu(Off)
  menu_manager.register_menu(Brightness)
  menu_manager.register_menu(Temperature)
  menu_manager.register_menu(Humidity)
  menu_manager.register_menu(RainProbability)
  menu_manager.initialize()
