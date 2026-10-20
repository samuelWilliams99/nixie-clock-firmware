class Digit:
  current_number = 0
  current_number_brightness = 0
  comma_left = 0
  comma_right = 0
  
  def __init__(self, set_pca_output):
    self.set_pca_output = set_pca_output
    self.reset()

  # Set number as None to adjust brightness of current number
  def set_digit(self, number, brightness):
    assert number >= 0 and number <= 9

    changed_number = number != self.current_number
    changed_brightness = brightness != self.current_number_brightness

    if not changed_number and not changed_brightness:
      return

    if number != None and changed_number:
      if self.current_number_brightness != 0:
        self.set_led(self.current_number, 0)
      self.current_number = number

    self.set_led(self.current_number, brightness)
    self.current_number_brightness = brightness

  def set_commas(self, comma_l, comma_r):
    if comma_l != self.comma_left:
      self.comma_left = comma_l
      self.set_led(10, comma_l)
    if comma_r != self.comma_right:
      self.comma_right = comma_r
      self.set_led(11, comma_r)

  # 0-9 is numbers, 10 is comma_l and 11 is comma_r
  def set_led(self, light_num, brightness):
    if light_num == 10:
      self.set_pca_output(11, brightness)
    elif light_num == 11:
      self.set_pca_output(10, brightness)
    elif light_num > 1:
      self.set_pca_output(11-light_num, brightness)
    else:
      self.set_pca_output(1-light_num, brightness)

  def clear_digit(self):
    self.set_digit(None, 0)

  def clear_commas(self):
    self.set_commas(0, 0)

  def clear(self):
    self.clear_digit()
    self.clear_commas()

  def reset(self):
    for i in range(12):
      self.set_led(i, 0)
