import imaplib
import logging
import random

import cache
import messageinfo
import stringscanner

MAILBOX_GMAIL_ALL_MAIL = "[Gmail]/All Mail"
MAILBOX_GMAIL_PREFIX = "[Gmail]"

class Mail(object):
  def __init__(self, server, use_ssl, username, password, 
      record=False, replay=False, max_messages=-1, random_subset=False):
    self.__server = server
    self.__username = username
    self.__record = record
    self.__replay = replay
    self.__max_messages = max_messages
    self.__random_subset = random_subset
    
    self.__current_mailbox = None
    
    if record or replay:
      self.__cache = cache.FileCache()
    
    imap_constructor = use_ssl and imaplib.IMAP4_SSL or imaplib.IMAP4
    
    logging.info("Connecting")
    
    self.__mail = imap_constructor(server)

    logging.info("Logging in")
    
    self.__mail.login(username, password)

  def GetMailboxes(self):
    logging.info("Getting mailboxes")
    
    r, mailboxes_data = self.__mail.list()
    self.__AssertOk(r)
    
    mailboxes = []
    for mailbox_data in mailboxes_data:
      s = stringscanner.StringScanner(mailbox_data)
      
      attributes = s.ConsumeValue()
      s.ConsumeAll(" ")
      delimiter = s.ConsumeValue()
      s.ConsumeAll(" ")
      name = s.ConsumeValue()
      
      if not "\\Noselect" in attributes and \
          name.find(MAILBOX_GMAIL_PREFIX) != 0:
        mailboxes.append(name)
    
    return mailboxes
  
  def SelectAllMail(self):
    self.SelectMailbox(MAILBOX_GMAIL_ALL_MAIL)

  def SelectMailbox(self, mailbox):
    logging.info("Selecting mailbox '%s'", mailbox)
    r, data = self.__mail.select(mailbox)
    self.__AssertOk(r)
    
    self.__current_mailbox = mailbox

  def GetMessageIds(self):
    message_infos = self.__UidFetch("ALL", "(INTERNALDATE RFC822.SIZE)")
    
    return [m.GetMessageId() for m in message_infos]

  def GetMessageInfos(self):
    return self.__UidFetch(
        "ALL", 
        "(UID FLAGS INTERNALDATE RFC822.SIZE RFC822.HEADER)",
        self.__max_messages)

  def Logout(self):
    logging.info("Logging out")
      
    self.__mail.close()
    self.__mail.logout()  

  def __UidFetch(self, search_criterion, fetch_parts, max_fetch=-1):
    logging.info("Fetching message infos")
    
    logging.info("  Fetching message list")
    data = self.__UidCommand("SEARCH", search_criterion)
    
    message_ids = data[0].split()

    logging.info("  %d messages were listed" % len(message_ids))

    if max_fetch != -1 and len(message_ids) > max_fetch:
      if self.__random_subset:
        # Pick random sample when there is a max, so that we get more 
        # interesting data. However, use the same seed so that runs will be 
        # deterministic and we can take advantage of record/replay
        random.seed(len(message_ids))
        
        # If possible, select a random sample from a recent subset of messages
        subset_size = max_fetch * 30
        if len(message_ids) > subset_size:
          message_ids = message_ids[-subset_size - 1:-1]
        
        message_ids = random.sample(message_ids, max_fetch)
      else:
        message_ids = message_ids[-max_fetch - 1:-1]
    
    message_infos = []
    
    # Fetch in smaller chunks, so that record/replay can be used when fetches
    # fail (to allow caching of successful chunks) and to have better progress
    # display
    chunk_size = fetch_parts.find("HEADER") != -1 and 1000 or 100000
    
    for i in xrange(0, len(message_ids), chunk_size):
      chunk_start = i
      chunk_end = i + chunk_size
      if chunk_end > len(message_ids):
        chunk_end = len(message_ids)
      
      chunk_message_ids = message_ids[chunk_start:chunk_end]
    
      logging.info("  Fetching info for %d messages (%d/%d)", 
          len(chunk_message_ids),
          chunk_end,
          len(message_ids))
    
      fetch_reply = self.__UidCommand(
          "FETCH",
          ",".join(chunk_message_ids), 
          fetch_parts)
    
      logging.info("  Parsing replies")
    
      message_infos.extend(self.__ParseFetchReply(fetch_reply))
    
    logging.info("  Got %d message infos" % len(message_infos))
    
    return message_infos

  def __UidCommand(self, command, *args):
    if self.__record or self.__replay:
      cache_key = "%s-%s-%s-%s-%s" % (
          self.__server, self.__username, self.__current_mailbox, 
          command, " ".join(args))

    if self.__replay:    
      cached_response = self.__cache.Get(cache_key)
      if cached_response:
        return cached_response
    
    r, data = self.__mail.uid(command, *args)
    self.__AssertOk(r)
    
    if self.__record:
      self.__cache.Set(cache_key, data)
    
    return data

  def __ParseFetchReply(self, fetch_reply):
    s = stringscanner.StringScanner(fetch_reply)
    
    message_infos = []
    
    while s.Peek():
      current_message_info = messageinfo.MessageInfo()
      message_infos.append(current_message_info)
      
      # The sequence ID is first, with all the data in parentheses
      sequence_id = s.ReadUntil(" ")
      s.ConsumeAll(" ")
      
      s.ConsumeChar("(")
      
      while s.Peek() != ")":
        s.ConsumeAll(" ")
        name = s.ReadUntil(" ")
        s.ConsumeAll(" ")
        
        value = s.ConsumeValue()
        
        current_message_info.PopulateField(name, value)
      
      s.ConsumeChar(")")
  
    return message_infos
  
  def __AssertOk(self, response):
    assert response == "OK"
