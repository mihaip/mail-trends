from base import *

class SizeFormatter(object):
  def __init__(self):
    self.header = "Size"
    self.css_class = "size sorting"
  
  def Format(self, message_info):
    return GetDisplaySize(message_info.size)

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

    return GetDisplaySize(bytes)    

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