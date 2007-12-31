import email
import calendar
import heapq
import sys
import time

from Cheetah.Template import Template
from pygooglechart import StackedVerticalBarChart, Axis

_Y_AXIS_SPACE = 32
_MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", 
    "Oct", "Nov", "Dec"]

def _GetYearRange(date_range):
  start, end = date_range
  start_year = time.localtime(start).tm_year
  end_year = time.localtime(end).tm_year
  return range(start_year, end_year + 1)

def _GetDisplaySize(bytes):
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
      rescaled_max = len(data) > 1500 and 61 or 4095
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

class BucketStat(ChartStat):
  def __init__(self, bucket_count, title, width, height):
    Stat.__init__(self) 
    
    self.__buckets = [0] * bucket_count
    self.__max = 0
    
    self.__title = title
    self.__width = width
    self.__height = height
  
  def ProcessMessageInfos(self, message_infos):
    for message_info in message_infos:
      bucket = self._GetBucket(message_info)
      
      if bucket is None: continue
      
      self.__buckets[bucket] += 1
      
      v = self.__buckets[bucket]
      if v > self.__max:
        self.__max = v
   
  def GetHtml(self):
    max = self._GetRescaledMax(self.__max)
    w = self.__width
    h = self.__height
    
    # We don't really care about StackedVerticalBarChart vs. 
    # GroupedVerticalBarChart since we just have one data-set, but only the
    # stacked graph seems to respect the bar spacing option
    chart = StackedVerticalBarChart(w, h)

    # Compute bar width so that it fits in the overall graph width.
    bucket_width = (w - _Y_AXIS_SPACE)/len(self.__buckets)
    bar_width = bucket_width * 4/5
    space_width = bucket_width - bar_width

    chart.set_bar_width(bar_width)
    chart.set_bar_spacing(space_width)
    
    chart.add_data(self._GetRescaledData(self.__buckets, max))
    chart.set_axis_range(Axis.LEFT, 0, max)
    chart.set_axis_labels(Axis.BOTTOM, self._GetBucketLabels())
    
    # We render the title in the template instead of in the chart, to give
    # stat collections and individual stats similar appearance
    
    t = Template(
        file="templates/bucket-stat.tmpl",
        searchList = {
          "id": self.id,
          "title": self.__title,
          "width": w,
          "height": h,
          "chart_url": chart.get_url()
        })
    return str(t)

class TimeOfDayStat(BucketStat):
  def __init__(self, title):
    BucketStat.__init__(self, 24, '%s by time of day' % title, 400, 200)
  
  def _GetBucket(self, message_info):
    return message_info.GetDate().tm_hour

  def _GetBucketLabels(self):
    return ['Midnight', '', '', '', '', '',
            '6 AM', '', '', '', '', '',
            'Noon', '', '', '', '', '',
            ' 6 PM', '', '', '', '', '']

class DayOfWeekStat(BucketStat):
  def __init__(self, title):
    BucketStat.__init__(self, 7, '%s by day of week' % title, 300, 200)

  
  def _GetBucket(self, message_info):
    # In the time tuple Monday is 0, but we want Sunday to be 0
    return (message_info.GetDate().tm_wday + 1) % 7
    
    
  def _GetBucketLabels(self):
    return ['S', 'M', 'T', 'W', 'T', 'F', 'S']

class YearStat(BucketStat):
  def __init__(self, date_range, title):
    self.__years = _GetYearRange(date_range)

    width = _Y_AXIS_SPACE + 30 * len(self.__years)
    
    BucketStat.__init__(
        self, len(self.__years), "%s by year" % title, width, 200)
    
  def _GetBucket(self, message_info):
    return message_info.GetDate().tm_year - self.__years[0]
  
  def _GetBucketLabels(self):
    return [str(x) for x in self.__years]
    
class MonthStat(BucketStat):
  def __init__(self, year):
    self.__year = year
    # No title is necessary, since the stat collection provides one
    BucketStat.__init__(self, 12, None, 300, 200)

  def _GetBucket(self, message_info):
    date = message_info.GetDate()
    
    if date.tm_year == self.__year:
      return date.tm_mon - 1
    else:
      return None
      
  def _GetBucketLabels(self):
    return _MONTH_NAMES

class DayStat(BucketStat):
  def __init__(self, year, month):
    self.__year = year
    self.__month = month
    self.__days_in_month = calendar.monthrange(year, month)[1]
    # No title is necessary, since the stat collection provides one
    BucketStat.__init__(
        self, 
        self.__days_in_month,
        None, 
        500,
        200)
        
  def _GetBucket(self, message_info):
    date = message_info.GetDate()
    
    if date.tm_year == self.__year and date.tm_mon == self.__month:
      return date.tm_mday - 1
    else:
      return None
      
  def _GetBucketLabels(self):
    return [str(d) for d in range(1, self.__days_in_month + 1)]

class SizeBucketStat(BucketStat):
  _SIZE_BUCKETS = [
    0,
    1 << 9,
    1 << 10,
    1 << 11,
    1 << 12,
    1 << 13,
    1 << 14,
    1 << 15,
    1 << 16,
    1 << 17,
    1 << 18,
    1 << 19,
    1 << 20,
    1 << 21,
    1 << 22,
    1 << 23,
  ]
  
  def __init__(self, title):
    BucketStat.__init__(
      self,
      len(SizeBucketStat._SIZE_BUCKETS),
      "%s message sizes" % title,
      500,
      200)

  def _GetBucket(self, message_info):
    size = message_info.size
    
    for i in reversed(xrange(0, len(SizeBucketStat._SIZE_BUCKETS))):
      if size >= SizeBucketStat._SIZE_BUCKETS[i]:
        return i
  
  def _GetBucketLabels(self):
    return [_GetDisplaySize(s) for s in SizeBucketStat._SIZE_BUCKETS]

class SizeFormatter(object):
  def __init__(self):
    self.header = "Size"
    self.css_class = "size"
  
  def Format(self, message_info):
    return _GetDisplaySize(message_info.size)

class SubjectSenderFormatter(object):
  def __init__(self):
    self.header = "Message"
    self.css_class = "message"
  
  def Format(self, message_info):
    name, address = message_info.GetSender()
      
    full_subject = subject = message_info.headers["subject"]
    if len(subject) > 50:
      subject = subject[0:50] + "..."

    t = Template(
        file="templates/subject-sender-formatter.tmpl",
        searchList = {
          "subject": subject,
          "full_subject": full_subject,
          "address": address,
          "name": name,
        });
    return str(t)    

class TableStat(Stat):
  _TABLE_SIZE = 40
  
  def __init__(self, title, formatters):
    Stat.__init__(self)
    self.__title = title
    
    self.__formatters = formatters

  def ProcessMessageInfos(self, message_infos):
    data = self._GetTableData(message_infos)
  
    heapq.heapify(data)
    
    table_data = []
    for i in range(0, min(len(data), TableStat._TABLE_SIZE)):
      table_data.append(heapq.heappop(data))
    
    self.__display_data = self._GetDisplayData(table_data)

  def GetHtml(self):
    t = Template(
        file="templates/table-stat.tmpl",
        searchList = {
          "id": self.id,
          "title": self.__title,
          "formatters": self.__formatters,
          "objs": self.__display_data
        })
    return str(t)

class SizeTableStat(TableStat):
  def __init__(self, title):
    TableStat.__init__(
        self,
        "%s top messages by size" % title,
        [SubjectSenderFormatter(), SizeFormatter()])

  def _GetTableData(self, message_infos):
    return [(sys.maxint - m.size, m) for m in message_infos]
  
  def _GetDisplayData(self, data):
    return [d[1] for d in data]

class SenderNameFormatter(object):
  def __init__(self):
    self.header = "Sender"
    self.css_class = "sender"

  def Format(self, sender):
    address, name, count, bytes = sender
    
    t = Template(
        file="templates/sender-formatter.tmpl",
        searchList = {
          "address": address,
          "name": name,
        });
    return str(t)    
    
class SenderCountFormatter(object):
  def __init__(self):
    self.header = "Msg. Count"
    self.css_class = "count"

  def Format(self, sender):
    address, name, count, bytes = sender
    
    return str(count)
    
class SenderBytesFormatter(object):
  def __init__(self):
    self.header = "Total Size"
    self.css_class = "size"
  
  def Format(self, sender):
    address, name, count, bytes = sender

    return _GetDisplaySize(bytes)    

class SenderTableStat(TableStat):
  def __init__(self, title):
    TableStat.__init__(
        self,
        "%s top senders" % title,
        [SenderNameFormatter(), SenderCountFormatter(), SenderBytesFormatter()])
  
  def _GetTableData(self, message_infos):
    sender_counts = {}
    sender_bytes = {}
    sender_names = {}
    
    for message_info in message_infos:
      name, address = message_info.GetSender()
      
      if not address: continue
      
      sender_counts[address] = sender_counts.get(address, 0) + 1
      sender_bytes[address] = sender_bytes.get(address, 0) + message_info.size
      sender_names[address] = name
      
    return [
      (
        sys.maxint - count, 
        address, 
        sender_names[address],
        sender_bytes[address]
      ) 
      for address, count in sender_counts.items()
    ]

  def _GetDisplayData(self, data):
    return [
      (address, name, sys.maxint - inverse_count, bytes) 
      for inverse_count, address, name, bytes in data
   ]

class ListNameFormatter(SenderNameFormatter):
  def __init__(self):
    SenderNameFormatter.__init__(self)
    self.header = "List"
    self.css_class = "list"

class ListIdTableStat(TableStat):
  def __init__(self, title):
    TableStat.__init__(
        self,
        "%s top lists" % title,
        [ListNameFormatter(), SenderCountFormatter(), SenderBytesFormatter()])
  
  def _GetTableData(self, message_infos):
    list_counts = {}
    list_bytes = {}
    list_names = {}
    
    for message_info in message_infos:
      name, address = message_info.GetListId()
      
      if not address: continue
      
      list_counts[address] = list_counts.get(address, 0) + 1
      list_bytes[address] = list_bytes.get(address, 0) + message_info.size
      list_names[address] = name
      
    return [
      (
        sys.maxint - count, 
        address, 
        list_names[address],
        list_bytes[address]
      ) 
      for address, count in list_counts.items()
    ]
    
  def _GetDisplayData(self, data):
    return [
      (address, name, sys.maxint - inverse_count, bytes) 
      for inverse_count, address, name, bytes in data
   ]    

class StatGroup(Stat):
  def __init__(self):
    Stat.__init__(self)
    self._stats = []
  
  def _AddStat(self, stat):
    self._stats.append(stat)
  
  def ProcessMessageInfos(self, message_infos):
    for stat in self._stats:
      stat.ProcessMessageInfos(message_infos)  

class StatCollection(StatGroup):
  def __init__(self, title):
    StatGroup.__init__(self)
    self.title = title
    self.__stat_titles = []
    
  def _AddStatRef(self, stat, title):
    self._AddStat(stat)
    self.__stat_titles.append(title)
    
  def GetHtml(self):
    t = Template(
        file="templates/stat-collection.tmpl", 
        searchList = {
          "collection": self, 
          "stats": self._stats,
          "titles": self.__stat_titles
        })
    return str(t)

class MonthStatCollection(StatCollection):
  def __init__(self, date_range, title):
    StatCollection.__init__(self, "%s by month for " % title)
    
    for year in _GetYearRange(date_range):
      self._AddStatRef(MonthStat(year), "%s" % year)
      
class DayStatCollection(StatCollection):
  def __init__(self, date_range, title):
    StatCollection.__init__(self, "%s by month for " % title)
    
    for year in _GetYearRange(date_range):
      for month in range(1, 13):
        self._AddStatRef(
            DayStat(year, month), 
            "%s %s" % (year, _MONTH_NAMES[month - 1]))
            
class StatColumnGroup(StatGroup):
  def __init__(self, *args):
    StatGroup.__init__(self)
    for stat in args:
      self._AddStat(stat)

  def GetHtml(self):
    t = Template(
        file="templates/stat-column-group.tmpl", 
        searchList = {"stats": self._stats})
    return str(t)
    
class StatTabGroup(StatGroup):
  def __init__(self, *tabs):
    StatGroup.__init__(self)
    
    self.__tabs = []
    for tab in tabs:
      title = tab[0]
      stats = tab[1:]
      
      for stat in stats:
        self._AddStat(stat)
      
      self.__tabs.append(StatTab(title, stats))
  
  def GetHtml(self):
    t = Template(
        file="templates/stat-tab-group.tmpl",
        searchList = {
          "id": self.id,
          "tabs": self.__tabs,
        })
    return str(t)    

class StatTab(object):
  _IdIndex = 0
  
  def __init__(self, title, stats):
    self.title = title
    self.stats = stats
    
    self.id = "tab-%d" % StatTab._IdIndex
    StatTab._IdIndex += 1

class TitleStat(Stat):
  _TIME_FORMAT = "%B %d %Y"
  
  def __init__(self, date_range, title):
    Stat.__init__(self)
    
    start_sec, end_sec = date_range
    self.__start = time.strftime(
        TitleStat._TIME_FORMAT, time.localtime(start_sec))
    self.__end = time.strftime(
        TitleStat._TIME_FORMAT, time.localtime(end_sec))
    
    self.__title = title
    
    self.__message_count = 0
  
  def ProcessMessageInfos(self, message_infos):
    self.__message_count = len(message_infos)
  
  def GetHtml(self):
    t = Template(
        file="templates/title-stat.tmpl",
        searchList = {
          "title": self.__title,
          "start": self.__start,
          "end": self.__end,
          "message_count": self.__message_count,
        })
    return str(t)