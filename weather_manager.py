from machine import Timer
import requests
import json
import _thread
from time import localtime
from location import latitude, longitude

class WeatherManager:
  # In celcius
  min_temperature = 0
  current_temperature = 0
  max_temperature = 0
  # 0-100 percentage
  min_humidity = 0
  current_humidity = 0
  max_humidity = 0
  # 0-100 percentage
  min_rain_probability = 0
  current_rain_probability = 0
  max_rain_probability = 0

  ready = False

  update_data_timer = Timer(-1)
  request_url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,relative_humidity_2m_max,relative_humidity_2m_min,precipitation_probability_min&hourly=precipitation_probability&current=temperature_2m,relative_humidity_2m&timezone=Europe%2FLondon&forecast_days=1&forecast_hours=1"

  def __init__(self):
    pass

  def clock_ready(self):
    self.trigger_update_next_hour(True)

  def trigger_update_next_hour(self, trigger_now = False):
    def callback(t):
      t.deinit()
      _thread.start_new_thread(self.update_data, [])
    if trigger_now:
      delay = 1
    else:
      t = localtime()
      delay = (60 - t[4]) * 60
    print(f"Next weather update in {delay} seconds")
    self.update_data_timer.init(mode=Timer.ONE_SHOT, period=delay * 1000, callback=callback)

  # Should be run in a bg thread
  # Calls self every hour
  def update_data(self):
    res = requests.get(self.request_url)
    if res.status_code != 200:
      print(res)
      return
    content = json.loads(res.content)
    current = content.get("current")
    hourly = content.get("hourly")
    daily = content.get("daily")

    self.min_temperature = round(daily.get("temperature_2m_min")[0])
    self.current_temperature = round(current.get("temperature_2m"))
    self.max_temperature = round(daily.get("temperature_2m_max")[0])

    self.min_humidity = round(daily.get("relative_humidity_2m_min")[0])
    self.current_humidity = round(current.get("relative_humidity_2m"))
    self.max_humidity = round(daily.get("relative_humidity_2m_max")[0])

    self.min_rain_probability = round(daily.get("precipitation_probability_min")[0])
    self.current_rain_probability = round(hourly.get("precipitation_probability")[0])
    self.max_rain_probability = round(daily.get("precipitation_probability_max")[0])

    self.ready = True

    self.trigger_update_next_hour()
