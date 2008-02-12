import math

from pygooglechart import ExtendedData, SimpleLineChart, Axis

from base import *

_FILL_COLORS = [
  'F4A674',
  '79ED29',
  'F376F3',
  '71C1FF',
  'FF6161',
  '598B26',
  '3C0079',
  '5D5D5D',
  'F12626',
  'F0F071',
]

class Distribution(ChartStat):
  _BUCKET_SIZE = 5
  _BUCKET_COUNT = int(math.floor(365/_BUCKET_SIZE))

  def __init__(self, year, css_class):
    ChartStat.__init__(self)
    
    self.__year = year
    self.__css_class = css_class
    self.__buckets = [{} for i in xrange(0, ListDistribution._BUCKET_COUNT)]
    self.__min_bucket = sys.maxint
    self.__max_bucket = -sys.maxint - 1
    self.__all_addresses = {}
    self.__address_names = {}
   
  def ProcessMessageInfos(self, message_infos, threads):
    for message_info in message_infos:
      date = message_info.GetDate()
      
      if date.tm_year != self.__year: continue

      bucket_index = (date.tm_yday - 1) / Distribution._BUCKET_SIZE
      
      # Ignore the last partial week bucket of the year
      if bucket_index >= Distribution._BUCKET_COUNT: continue

      for name, address in self._GetAddresses(message_info):
        self.__address_names[address] = name
        
        if not address: continue
  
        self.__all_addresses[address] = \
            self.__all_addresses.get(address, 0) + 1
  
        bucket = self.__buckets[bucket_index]
        
        if bucket_index > self.__max_bucket: self.__max_bucket = bucket_index
        if bucket_index < self.__min_bucket: self.__min_bucket = bucket_index
        
        bucket[address] = bucket.get(address, 0) + 1

  def GetHtml(self):
    # Determine top 10 addresses
    top_addresses = \
        [(count, address) for (address, count) in self.__all_addresses.items()]
    top_addresses.sort(reverse=True)
    top_addresses = [address for (count, address) in top_addresses]
    
    if len(top_addresses) > 10:
      top_addresses = top_addresses[0:10]
    
    top_addresses.reverse()

    # Collect lines for each address
    bucket_lines = {}
    
    for bucket in self.__buckets:
      sum = 0
      for address in top_addresses:
        sum += bucket.get(address, 0)
      
      sum = float(sum)
      fraction_sum = 0
      
      for address in top_addresses:
        if sum == 0:
          fraction = 0
        else:
          fraction = bucket.get(address, 0)/sum
      
        fraction_sum += fraction
        
        # Make sure everything adds up to 1.0
        if address == top_addresses[-1]:
          fraction_sum = 1.0
        
        if address not in bucket_lines:
          bucket_lines[address] = []

        bucket_lines[address].append(round(
            fraction_sum * ExtendedData.max_value()))

    # Smooth lines
    for address, points in bucket_lines.items():
      smoothed = []
      window = []
      window_sum = 0
      for i in xrange(0, len(points)):
        if i < self.__min_bucket or i > self.__max_bucket:
          smoothed.append(0)
        else:
          point = points[i]
          if len(window) == Distribution._BUCKET_SIZE:
            window_sum -= window.pop(0)
          window.append(point)
          window_sum += point
          smoothed.append(round(window_sum/len(window)))
      bucket_lines[address] = smoothed
    
    # Generate chart
    chart = SimpleLineChart(450, 250)
    data_index = 0
    colors = []
    legend = []
    
    top_addresses.reverse()
    
    for address in top_addresses:
      data = bucket_lines[address]
      chart.add_data(data)
      
      color = _FILL_COLORS[data_index % len(_FILL_COLORS)]
      
      chart.add_fill_range(
          color,
          data_index,
          data_index + 1)
      data_index += 1

      colors.append(color)
      legend.append((color, self.__address_names[address], address))

    # Another set of points to make sure we will to the bottom
    chart.add_data([0, 0])
    
    chart.set_colours(colors)
    chart.set_axis_labels(Axis.BOTTOM, MONTH_NAMES)

    t = Template(
        file="templates/distribution.tmpl",
        searchList = {
          "id": self.id,
          "chart": chart,
          # We don't use the legend feature of the chart API since that would
          # make the URL longer than its limits
          "legend": legend, 
          "class": self.__css_class,
        })
    return unicode(t)

class SenderDistribution(Distribution):
  def __init__(self, year):
    Distribution.__init__(self, year, "sender")
  
  def _GetAddresses(self, message_info):
    return [message_info.GetSender()]

class RecipientDistribution(Distribution):
  def __init__(self, year):
    Distribution.__init__(self, year, "recipient")
  
  def _GetAddresses(self, message_info):
    return message_info.GetRecipients()
    
class ListDistribution(Distribution):
  def __init__(self, year):
    Distribution.__init__(self, year, "list")
    
  def _GetAddresses(self, message_info):
    return [message_info.GetListId()]