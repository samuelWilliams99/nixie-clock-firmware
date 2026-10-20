from micropython_pca9685 import PCA9685
from machine import Pin, I2C, Signal
from digit import Digit

class Display:
  def __init__(self):
    self.leds_controllers = Signal(Pin(2, Pin.OUT), invert=True)
    self.high_voltage = Signal(Pin(3, Pin.OUT))
    self.disable()
    i2c = I2C(0, sda=Pin(20), scl=Pin(21))  # Correct I2C pins for RP2040
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

  def disable(self):
    self.leds_controllers.off()
    self.high_voltage.off()

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

  def set_digit(self, digit_index, number, value):
    assert digit_index >= 0 and digit_index <= 5
    self.digits[digit_index].set_digit(number, value)

  def set_digit_commas(self, digit_index, comma_l, comma_r):
    assert digit_index >= 0 and digit_index <= 5
    self.digits[digit_index].set_digit(comma_l, comma_r)
