import menu_manager
from machine import Timer

def main(t=None):
  if t != None: t.deinit()
  menu_manager.main()

# Drop this when debugging
Timer(-1).init(mode=Timer.ONE_SHOT, period=5000, callback=main)