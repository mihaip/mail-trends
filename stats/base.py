import email
import calendar
import heapq
import sys
import time

from Cheetah.Template import Template
from pygooglechart import ExtendedData
from pygooglechart import SimpleData

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", 
    "Oct", "Nov", "Dec"]

def GetYearRange(date_range):
  start, end = date_range
  start_year = time.localtime(start).tm_year
  end_year = time.localtime(end).tm_year
  return range(start_year, end_year + 1)

def GetDisplaySize(bytes):
  megabytes = bytes/(1 << 20)
  
  if megabytes:
    if bytes % (1 << 20) == 0:
      return "%dM" % (bytes/(1 << 20))
    else:
      return "%.2fM" % (float(bytes)/float(1 << 20))
  
  kilobytes = bytes/(1 << 10)
  
  if kilobytes:
    if bytes % (1 << 10) == 0:
      return "%dK" % (bytes/(1 << 10))
    else:
      return "%.2fK" % (float(bytes)/float(1 << 10))

  return str(bytes)
  
class Stat(object):
  _IdIndex = 0

  def __init__(self):
    self.id = "stat-%d" % Stat._IdIndex
    Stat._IdIndex += 1
  
class ChartStat(Stat):
  def __init__(self):
    Stat.__init__(self)
    
  def _GetRescaledData(self, data, data_max):
    # Use the extended encoding if we don't have too many data points
    if data_max:
      rescaled_max = (len(data) > 1500 and \
          SimpleData.max_value() or ExtendedData.max_value())
      scaling_factor = float(rescaled_max) / float(data_max)
    else:
      scaling_factor = 0
    
    scaled_data = []
    
    for point in data:
      scaled_data.append(int(float(point) * scaling_factor))
    
    return scaled_data
  
  def _GetRescaledMax(self, max):
    if max > 200:
      if max % 100:
        return max + (100 - (max % 100))
      else:
        return max
    else:
      if max % 10:
        return max + (10 - (max % 10))
      else:
        return max

class TitleStat(Stat):
  _TIME_FORMAT = "%B %d %Y"
  
  def __init__(self, date_range):
    Stat.__init__(self)
    
    start_sec, end_sec = date_range
    self.__start = time.strftime(
        TitleStat._TIME_FORMAT, time.localtime(start_sec))
    self.__end = time.strftime(
        TitleStat._TIME_FORMAT, time.localtime(end_sec))
    
    self.__message_count = 0
  
  def ProcessMessageInfos(self, message_infos, threads):
    self.__message_count = len(message_infos)
    self.__thread_count = len(threads)
  
  def GetHtml(self):
    t = Template(
        file="templates/title-stat.tmpl",
        searchList = {
          "start": self.__start,
          "end": self.__end,
          "message_count": self.__message_count,
          "thread_count": self.__thread_count
        })
    return unicode(t)