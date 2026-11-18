from pca9685 import PCA9685
from machine import Pin, I2C, Signal
from digit import Digit
import math

class Display:
  enabled = False
  # Whether updates to display should pulse higher brightness
  update_glow = False
  normal_brightness = 0x4FFF
  glow_brightness = 0xEFFF
  # Float from 0 to 1 for glow amount
  digit_glows = [0.0] * 6
  # Used only for glows, each digit tracks its own actual updates to the led drivers
  digit_prev_values = [None] * 6
  def __init__(self):
    self.leds_controllers = Signal(Pin(2, Pin.OUT), invert=True)
    self.high_voltage = Signal(Pin(3, Pin.OUT))
    self.disable()
    i2c = I2C(0, sda=Pin(20), scl=Pin(21))
    self.pcas = [
      PCA9685(i2c, address=69),
      PCA9685(i2c, address=68),
      PCA9685(i2c, address=67),
      PCA9685(i2c, address=66),
      PCA9685(i2c, address=65)
    ]
    for pca in self.pcas:
      pca.frequency = 60

    self.digits = [
      Digit(lambda output, value: self.set_pca_output(0, output, value)),
      Digit(lambda output, value: self.set_pca_output(1, output, value)),
      Digit(lambda output, value: self.set_pca_output(2, output, value)),
      Digit(lambda output, value: self.set_pca_output(3, output, value)),
      Digit(lambda output, value: self.set_pca_output(4, output, value)),
      Digit(lambda output, value: self.set_sixth_digit_value(output, value)),
    ]

  def enable(self):
    self.leds_controllers.on()
    self.high_voltage.on()
    self.enabled = True

  def disable(self):
    self.leds_controllers.off()
    self.high_voltage.off()
    self.enabled = False

  def set_enabled(self, enabled):
    if enabled: self.enable()
    else: self.disable()

  # The sixth digit controls are split across 3 PCAs
  def set_sixth_digit_value(self, output, value):
    if output <= 3:
      self.set_pca_output(2, output + 12, value)
    elif output <= 7:
      self.set_pca_output(4, output + 8, value)
    else:
      self.set_pca_output(3, output + 4, value)

  def set_pca_output(self, pca_index, output, value):
    self.pcas[pca_index].channels[output].duty_cycle = value

  def set_update_glow(self, update_glow):
    self.update_glow = update_glow
    self.digit_glows = [0.0] * 6

  def to_digit_brightness(self, digit_index):
    if not self.update_glow: return self.normal_brightness
    return self.normal_brightness + math.floor(self.digit_glows[digit_index] * (self.glow_brightness - self.normal_brightness))

  # Takes the number of "ticks" (i.e. calls to this function) to return a digit to normal brightness
  def tick_update_glows(self, tick_count):
    # Reduce the digit glow by 1/tick_count
    diff = 1/tick_count
    for digit_index in range(6):
      if self.digit_glows[digit_index] > 0.0:
        self.digit_glows[digit_index] = max(0, self.digit_glows[digit_index] - diff)
        self.digits[digit_index].set_digit(self.digit_prev_values[digit_index], self.to_digit_brightness(digit_index))

  # Handles updating the digit_glows for a set event
  def update_glows_for_digit_change(self, digit_index, number):
    if number == None:
      self.digit_glows[digit_index] = 0.0
    else:
      if self.update_glow and number != self.digit_prev_values[digit_index]:
        self.digit_glows[digit_index] = 1.0
    self.digit_prev_values[digit_index] = number

  # Number can be None to mean off, which we show as a 0 with value 0
  def set_digit(self, digit_index, number):
    assert digit_index >= 0 and digit_index <= 5
    self.update_glows_for_digit_change(digit_index, number)
    value = 0 if number == None else self.to_digit_brightness(digit_index)

    self.digits[digit_index].set_digit(number or 0, value)

  def to_comma_brightness(self, is_on):
    return self.normal_brightness if is_on else 0

  def set_digit_commas(self, digit_index, comma_l, comma_r):
    assert digit_index >= 0 and digit_index <= 5
    self.digits[digit_index].set_commas(self.to_comma_brightness(comma_l), self.to_comma_brightness(comma_r))
