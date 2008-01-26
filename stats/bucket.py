from base import *

_Y_AXIS_SPACE = 36

class BucketStat(ChartStat):
  def __init__(self, bucket_count, title, width, height):
    ChartStat.__init__(self) 
    
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
    self.__years = GetYearRange(date_range)

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
    return MONTH_NAMES

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
    return [GetDisplaySize(s) for s in SizeBucketStat._SIZE_BUCKETS]

class ThreadSizeBucketStat(BucketStat):
  _SIZE_BUCKETS = [
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8,
    9,
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