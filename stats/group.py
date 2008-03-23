from base import *
from bucket import *
from distribution import *

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
    all_empty = True
    
    for stat in self._stats:
      if not stat.IsEmpty():
        all_empty = False
        break
    
    if all_empty: return ""
    
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

    for year in GetYearRange(date_range):
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
            "%s %s" % (year, MONTH_NAMES[month - 1]))

class SenderDistributionStatCollection(StatCollection):
  def __init__(self, date_range):
    StatCollection.__init__(self, "Sender distribution for ")

    for year in GetYearRange(date_range):
      self._AddStatRef(SenderDistribution(year), "%s" % year)

class RecipientDistributionStatCollection(StatCollection):
  def __init__(self, date_range):
    StatCollection.__init__(self, "Recipient distribution for ")

    for year in GetYearRange(date_range):
      self._AddStatRef(RecipientDistribution(year), "%s" % year)

class ListDistributionStatCollection(StatCollection):
  def __init__(self, date_range):
    StatCollection.__init__(self, "List distribution for ")

    for year in GetYearRange(date_range):
      self._AddStatRef(ListDistribution(year), "%s" % year)

class MeRecipientDistributionStatCollection(StatCollection):
  def __init__(self, date_range):
    StatCollection.__init__(self, "Recipients from me distribution for ")

    for year in GetYearRange(date_range):
      self._AddStatRef(MeRecipientDistribution(year), "%s" % year)

class MeSenderDistributionStatCollection(StatCollection):
  def __init__(self, date_range):
    StatCollection.__init__(self, "Sender to me distribution for ")

    for year in GetYearRange(date_range):
      self._AddStatRef(MeSenderDistribution(year), "%s" % year)
            
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