from machine import Pin, I2C, Timer
import mpr121

class ButtonManager:
  # False is just to return a value, doesn't actually matter
  handler = lambda button, is_pressed: False
  timer = Timer(-1)
  last_bitflags = 0
  def __init__(self):
    i2c = I2C(1, sda=Pin(10), scl=Pin(11), freq=100000)
    self.mpr = mpr121.MPR121(i2c, 0x5A)
    # Start timer for querying the button state, something like 1/10 should be enough
    def callback(_t):
      bitflags = self.mpr.touched()
      diff = self.last_bitflags ^ bitflags
      for i in range(12):
        if (diff & (1 << i)):
          mapped_button = self.map_button(i)
          if mapped_button != None: self.handler(mapped_button, True if bitflags & (1 << i) else False)

      self.last_bitflags = bitflags

    self.timer.init(period=100, callback=callback)
    pass

  # Maps from mpr index to button number (0-5 left to right)
  def map_button(self, button):
    if (button == 6): return 1
    if (button == 7): return 0
    if (button == 8): return 5 # ignored?
    if (button == 9): return 4
    if (button == 10): return 2
    if (button == 11): return 3
    print("wrong button index somehow? " + str(button))
    return None

  # Handler takes button (0-5) and is_pressed (bool)
  def set_handler(self, handler):
    self.handler = handler
