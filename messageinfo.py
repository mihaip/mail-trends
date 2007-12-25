import email
import imaplib
import md5
import time

import re

InternalDate = re.compile(r'.*INTERNALDATE "'
        r'(?P<day>[ 0123][0-9])-(?P<mon>[A-Z][a-z][a-z])-(?P<year>[0-9][0-9][0-9][0-9])'
        r' (?P<hour>[0-9][0-9]):(?P<min>[0-9][0-9]):(?P<sec>[0-9][0-9])'
        r' (?P<zonen>[-+])(?P<zoneh>[0-9][0-9])(?P<zonem>[0-9][0-9])'
        r'"')

class MessageInfo(object):
  __oldestMessageSec = time.mktime([2027, 12, 31, 23, 59, 59, 0, 0, 0]) 
  __newestMessageSec = time.mktime([1970, 1, 1, 0, 0, 0, 0, 0, 0]) 
  __parseDates = True
  
  def __init__(self): 
    self.__message_id = None
    self.__mailboxes = []
  
  def PopulateField(self, name, value):
    if name == "UID": self.__uid = value
    elif name == "RFC822.SIZE": self.__size = int(value)
    elif name == "FLAGS": self.__flags = value
    elif name == "INTERNALDATE":
      self.__date_string = value

      if MessageInfo.__parseDates:
        self.__date_tuple = \
            imaplib.Internaldate2tuple('INTERNALDATE "%s"' % value)
        
        self.__date_sec = time.mktime(self.__date_tuple)
        if self.__date_sec > MessageInfo.__newestMessageSec:
          MessageInfo.__newestMessageSec = self.__date_sec
        if self.__date_sec < MessageInfo.__oldestMessageSec:
          MessageInfo.__oldestMessageSec = self.__date_sec
      
    elif name == "RFC822.HEADER": 
        self.__headers = email.message_from_string(value)
    else: raise AssertionError("unknown field: %s" % name)

  def GetMessageId(self):
    if not self.__message_id:
      d = md5.new()
      d.update(str(self.__size))
      d.update(self.__date_string)
      self.__message_id = d.digest()
    return self.__message_id

  def AddMailbox(self, mailbox):
    self.__mailboxes.append(mailbox)

  def GetDate(self):
    return self.__date_tuple

  def GetDateRange():
    return [MessageInfo.__oldestMessageSec, MessageInfo.__newestMessageSec]
  GetDateRange = staticmethod(GetDateRange)
  
  def SetParseDate(parseDates):
    MessageInfo.__parseDates = parseDates
  SetParseDate = staticmethod(SetParseDate)

  def __str__(self):
    return "%s (size: %d, date: %s)" % (
        self.__headers["subject"], self.__size, self.__date_string)