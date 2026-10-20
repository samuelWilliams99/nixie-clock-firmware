from machine import Pin, I2C, Signal, RTC

from time import sleep, localtime, time_ns, sleep_us, gmtime
import ntptime
import math


def sleepUntilNextFraction(denominator):
  next_interval = 1000000 // denominator
  time_us = time_ns() // 1000
  sleep_us(next_interval - (time_us % next_interval))

def main():
  leds_controllers.on()
  clearScreen()
  high_voltage.on()
  # Set the PWM duty cycle for channel zero to 50%. duty_cycle is 16 bits to match other PWM objects
  # but the PCA9685 will only actually give 12 bits of resolution.

  last_hour = -1
  last_min = -1
  last_sec = -1
  ticks_per_second = 12
  interval_counter = 0

  sleepUntilNextFraction(1)

  for _ in range(60 * ticks_per_second):
    if interval_counter == 0:
      t = localtime()
      if t[3] != last_hour:
        last_hour = t[3]
        displayNumber(0, 1, last_hour, 0x7FFF)

      if t[4] != last_min:
        last_min = t[4]
        displayNumber(2, 3, last_min, 0x7FFF)

      if t[5] != last_sec:
        last_sec = t[5]
        displayNumber(4, 5, last_sec, 0x7FFF)

    for i in range(6):
      clearCommas(i)

    cycle_r = (interval_counter % 2) * 0x7FFF
    cycle_l = 0x7FFF - cycle_r
    setCommas(interval_counter // 2, cycle_l, cycle_r)

    # If end of interval, sleep until next full second
    interval_counter = interval_counter + 1
    if interval_counter == ticks_per_second:
      interval_counter = 0
      sleepUntilNextFraction(1)
    else:
      sleepUntilNextFraction(ticks_per_second)

  off()

def off():
  leds_controllers.off()
  high_voltage.off()
