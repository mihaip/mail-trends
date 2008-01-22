import email
import calendar
import heapq
import sys
import time

from Cheetah.Template import Template
from pygooglechart import StackedVerticalBarChart, Axis

_Y_AXIS_SPACE = 36
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
 
  def _GetBucketCollection(self, message_infos, threads):
    return message_infos
 
  def ProcessMessageInfos(self, message_infos, threads):
    for bucket_obj in self._GetBucketCollection(message_infos, threads):
      bucket = self._GetBucket(bucket_obj)
      
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
    return unicode(t)

class TimeOfDayStat(BucketStat):
  def __init__(self):
    BucketStat.__init__(self, 24, 'Time of day', 400, 200)
  
  def _GetBucket(self, message_info):
    return message_info.GetDate().tm_hour

  def _GetBucketLabels(self):
    return ['Midnight', '', '', '', '', '',
            '6 AM', '', '', '', '', '',
            'Noon', '', '', '', '', '',
            ' 6 PM', '', '', '', '', '']

class DayOfWeekStat(BucketStat):
  def __init__(self):
    BucketStat.__init__(self, 7, 'Day of week', 300, 200)

  
  def _GetBucket(self, message_info):
    # In the time tuple Monday is 0, but we want Sunday to be 0
    return (message_info.GetDate().tm_wday + 1) % 7
    
    
  def _GetBucketLabels(self):
    return ['S', 'M', 'T', 'W', 'T', 'F', 'S']

class YearStat(BucketStat):
  def __init__(self, date_range):
    self.__years = _GetYearRange(date_range)

    width = _Y_AXIS_SPACE + 30 * len(self.__years)
    
    BucketStat.__init__(
        self, len(self.__years), "Year", width, 200)
    
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
  
  def __init__(self):
    BucketStat.__init__(
      self,
      len(SizeBucketStat._SIZE_BUCKETS),
      "Message sizes",
      500,
      200)

  def _GetBucket(self, message_info):
    size = message_info.size
    
    for i in reversed(xrange(0, len(SizeBucketStat._SIZE_BUCKETS))):
      if size >= SizeBucketStat._SIZE_BUCKETS[i]:
        return i
  
  def _GetBucketLabels(self):
    return [_GetDisplaySize(s) for s in SizeBucketStat._SIZE_BUCKETS]

class ThreadSizeBucketStat(BucketStat):
  _SIZE_BUCKETS = [
    1,
    5,
    10,
    20,
    30,
    40,
    50,
    100,
    150,
    200,
  ]
  
  def __init__(self):
    BucketStat.__init__(
      self,
      len(ThreadSizeBucketStat._SIZE_BUCKETS),      
      "Thread lengths",
      500,
      200)
      
  def _GetBucketCollection(self, message_infos, threads):
    return threads      
  
  def _GetBucket(self, thread):
    size = len(thread)
    
    for i in reversed(xrange(0, len(ThreadSizeBucketStat._SIZE_BUCKETS))):
      if size >= ThreadSizeBucketStat._SIZE_BUCKETS[i]:
        return i

  def _GetBucketLabels(self):
    return [str(s) for s in ThreadSizeBucketStat._SIZE_BUCKETS]

class SizeFormatter(object):
  def __init__(self):
    self.header = "Size"
    self.css_class = "size sorting"
  
  def Format(self, message_info):
    return _GetDisplaySize(message_info.size)

class SubjectSenderFormatter(object):
  def __init__(self):
    self.header = "Message"
    self.css_class = "message"
  
  def Format(self, message_info):
    t = Template(
        file="templates/subject-sender-formatter.tmpl",
        searchList = {
          "message_info": message_info,
          "connector": "from"
        });
    return unicode(t)    

class TableStat(Stat):
  _TABLE_SIZE = 40
  
  def __init__(self, title, formatters):
    Stat.__init__(self)
    self.__title = title
    
    self.__formatters = formatters

  def ProcessMessageInfos(self, message_infos, threads):
    data = self._GetTableData(message_infos, threads)
  
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
    return unicode(t)

class SizeTableStat(TableStat):
  def __init__(self):
    TableStat.__init__(
        self,
        "Top messages by size",
        [SubjectSenderFormatter(), SizeFormatter()])

  def _GetTableData(self, message_infos, threads):
    return [(sys.maxint - m.size, m) for m in message_infos]
  
  def _GetDisplayData(self, data):
    return [d[1] for d in data]

class ThreadSubjectFormatter(object):
  def __init__(self):
    self.header = "Subject"
    self.css_class = "subject"
  
  def Format(self, thread):
    if thread.message and thread.message.message_info:
      t = Template(
          file="templates/subject-sender-formatter.tmpl",
          searchList = {
            "message_info": thread.message.message_info,
            "connector": "started by"
          });
    else:
      t = Template(
          file="templates/subject-formatter.tmpl",
          searchList = {
            "subject": thread.subject,
            "connector": "started by"
          });
    return unicode(t)    
    
class ThreadSizeFormatter(object):
  def __init__(self):
    self.header = "Length"
    self.css_class = "length sorting"
  
  def Format(self, thread):
    return len(thread)

class ThreadSizeTableStat(TableStat):
  def __init__(self):
    TableStat.__init__(
        self,
        "Top threads",
        [ThreadSubjectFormatter(), ThreadSizeFormatter()])

  def _GetTableData(self, message_infos, threads):
    return [(sys.maxint - len(t), t) for t in threads]
  
  def _GetDisplayData(self, data):
    return [d[1] for d in data]

class ThreadOriginFormatter(object):
  def __init__(self, header, css_class):
    self.header = header
    self.css_class = css_class
    
  def Format(self, thread_info):
    t = Template(
        file="templates/address-formatter.tmpl",
        searchList = {
          "address": thread_info["address"],
          "name": thread_info["name"],
        });
    return unicode(t)

class ThreadOriginSizeFormatter(object):
  def __init__(self):
    self.header = "Avg. Length"
    self.css_class = "length sorting"
    
  def Format(self, thread_info):
    return "%.2f" % (
        float(thread_info["total_size"])/float(thread_info["count"]))
        
class ThreadCountFormatter(object):
  def __init__(self):
    self.header = "Count"
    self.css_class = "count"
    
  def Format(self, thread_info):
    return "%d" % thread_info["count"]

class ThreadOriginTableStat(TableStat):
  def __init__(self, title, column_header, column_css_class):
    TableStat.__init__(
      self,
      title,
      [ThreadOriginFormatter(column_header, column_css_class), 
          ThreadOriginSizeFormatter(),
          ThreadCountFormatter()])
 
  def _GetTableData(self, message_infos, threads):
    origin_threads = {}
    
    for thread in threads:
      origin = self._GetThreadOrigin(thread)
      
      if not origin: continue

      origin_name, origin_address = origin
      
      if origin_address in origin_threads:
        origin_thread_info = origin_threads[origin_address]
      else:
        origin_thread_info = {
          "address": origin_address,
          "name": "",
          "count": 0,
          "total_size": 0,
        }
        origin_threads[origin_address] = origin_thread_info
          
      if origin_name:
        origin_thread_info["name"] = origin_name
      origin_thread_info["count"] += 1
      origin_thread_info["total_size"] += len(thread)
    
    return [
      (sys.maxint - i["total_size"]/i["count"], i) \
          for origin_address, i in origin_threads.items()
    ]
   
  def _GetDisplayData(self, data):
    return [d[1] for d in data]  

class ThreadStarterTableStat(ThreadOriginTableStat):
  def __init__(self):
    ThreadOriginTableStat.__init__(
      self,
      "Top thread starters",
      "Starter",
      "sender")
  
  def _GetThreadOrigin(self, thread):
    if thread.message and thread.message.message_info:
      return thread.message.message_info.GetSender()
    else:
      return None

class ThreadListTableStat(ThreadOriginTableStat):
  def __init__(self):
    ThreadOriginTableStat.__init__(
        self,
        "Top thread lists",
        "List",
        "list")
  
  def _GetThreadOrigin(self, thread):
    if thread.message and thread.message.message_info:
      return thread.message.message_info.GetListId()
    else:
      return None    

class AddressNameFormatter(object):
  def __init__(self, header, css_class):
    self.header = header
    self.css_class = css_class

  def Format(self, data):
    address, name, count, bytes = data
    
    t = Template(
        file="templates/address-formatter.tmpl",
        searchList = {
          "address": address,
          "name": name,
        });
    return unicode(t)    
    
class AddressCountFormatter(object):
  def __init__(self):
    self.header = "Msg. Count"
    self.css_class = "count sorting"

  def Format(self, data):
    address, name, count, bytes = data
    
    return str(count)
    
class AddressBytesFormatter(object):
  def __init__(self):
    self.header = "Total Size"
    self.css_class = "size"
  
  def Format(self, data):
    address, name, count, bytes = data

    return _GetDisplaySize(bytes)    

class UniqueAddressTableStat(TableStat):
  def __init__(self, title, column_title, column_css_class):
    TableStat.__init__(
      self,
      title,
      [
        AddressNameFormatter(column_title, column_css_class),
        AddressCountFormatter(),
        AddressBytesFormatter(),
      ])
  
  def _GetTableData(self, message_infos, threads):
    address_counts = {}
    address_bytes = {}
    address_names = {}
    
    for message_info in message_infos:
      for name, address in self._GetAddresses(message_info):
        if not address: continue
        
        address_counts[address] = address_counts.get(address, 0) + 1
        address_bytes[address] = \
            address_bytes.get(address, 0) + message_info.size
        address_names[address] = name
      
    return [
      (
        sys.maxint - count, 
        address, 
        address_names[address],
        address_bytes[address]
      ) 
      for address, count in address_counts.items()
    ]
  
  def _GetDisplayData(self, data):
    return [
      (address, name, sys.maxint - inverse_count, bytes) 
      for inverse_count, address, name, bytes in data
   ]
   
class SenderTableStat(UniqueAddressTableStat):
  def __init__(self):
    UniqueAddressTableStat.__init__(
        self,
        "Top senders",
        "Sender",
        "sender")
  
  def _GetAddresses(self, message_info):
    return [message_info.GetSender()]

class ListIdTableStat(UniqueAddressTableStat):
  def __init__(self):
    UniqueAddressTableStat.__init__(
        self,
        "Top lists",
        "List",
        "list")
  
  def _GetAddresses(self, message_info):
    return [message_info.GetListId()]

class RecipientTableStat(UniqueAddressTableStat):
  def __init__(self):
    UniqueAddressTableStat.__init__(
      self,
      "Top recipients",
      "Recipient",
      "recipient")
  
  def _GetAddresses(self, message_info):
    return message_info.GetRecipients()

class StatGroup(Stat):
  def __init__(self):
    Stat.__init__(self)
    self._stats = []
  
  def _AddStat(self, stat):
    self._stats.append(stat)
  
  def ProcessMessageInfos(self, message_infos, threads):
    for stat in self._stats:
      if stat:
        stat.ProcessMessageInfos(message_infos, threads) 

class StatCollection(StatGroup):
  def __init__(self, title):
    StatGroup.__init__(self)
    self.title = title
    self.__stat_titles = []
    
  def _AddStatRef(self, stat, title):
    self._AddStat(stat)
    self.__stat_titles.append(title)
  
  def _AddStatDivider(self):
    self._AddStat(None)
    self.__stat_titles.append(None)
  
  def GetHtml(self):
    t = Template(
        file="templates/stat-collection.tmpl", 
        searchList = {
          "collection": self, 
          "stats": self._stats,
          "titles": self.__stat_titles
        })
    return unicode(t)

class MonthStatCollection(StatCollection):
  def __init__(self, date_range):
    StatCollection.__init__(self, "Month by month for ")

    for year in _GetYearRange(date_range):
      self._AddStatRef(MonthStat(year), "%s" % year)
      
class DayStatCollection(StatCollection):
  def __init__(self, date_range):
    StatCollection.__init__(self, "Day by day for ")
    
    start, end = [time.localtime(d) for d in date_range]
    
    for year in range(start.tm_year, end.tm_year + 1):
      for month in range(1, 13):
        # skip over months before our range        
        if year == start.tm_year and month < start.tm_mon: continue
        
        # and those after
        if year == end.tm_year and month > end.tm_mon: continue
        
        # dividers between years
        if month == 1 and year != start.tm_year: self._AddStatDivider()
        
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
    return unicode(t)
    
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
    return unicode(t)    

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
  
  def ProcessMessageInfos(self, message_infos, threads):
    self.__message_count = len(message_infos)
    self.__thread_count = len(threads)
  
  def GetHtml(self):
    t = Template(
        file="templates/title-stat.tmpl",
        searchList = {
          "title": self.__title,
          "start": self.__start,
          "end": self.__end,
          "message_count": self.__message_count,
          "thread_count": self.__thread_count
        })
    return unicode(t)