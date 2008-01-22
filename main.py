#!/usr/bin/python

import codecs
import getopt
import logging
import messageinfo
import re
import sys

from Cheetah.Template import Template
import jwzthreading

import mail
import stats

def GetOptsMap():
  opts, args = getopt.getopt(sys.argv[1:], "", [
      # Standard options
      "username=", "password=", "use_ssl", "server=", 
      # Development options
      "record", "replay", "max_messages=", "skip_labels"])
  
  opts_map = {}
  for name, value in opts:
    opts_map[name[2:]] = value
  
  assert "username" in opts_map
  assert "password" in opts_map
  assert "server" in opts_map
  
  return opts_map

def GetMessageInfos(opts):
  m = mail.Mail(
      opts["server"], "use_ssl" in opts, opts["username"], opts["password"],
      "record" in opts, "replay" in opts, 
      "max_messages" in opts and int(opts["max_messages"]) or -1)
  
  # First, get all message infos
  m.SelectAllMail()
  
  message_infos = m.GetMessageInfos()
  
  # Then for each mailbox, see which messages are in it, and attach that to 
  # the mail info
  if "skip_labels" not in opts:
    message_infos_by_id = \
        dict([(mi.GetMessageId(), mi) for mi in message_infos])
    
    # Don't want to parse all these dates, since we already have them from the
    # message infos above.
    messageinfo.MessageInfo.SetParseDate(False)
    
    for mailbox in m.GetMailboxes():
      m.SelectMailbox(mailbox)
      message_ids = m.GetMessageIds()
      for mid in message_ids:
        if mid in message_infos_by_id:
          message_info = message_infos_by_id[mid]
          message_info.AddMailbox(mailbox)
  
    messageinfo.MessageInfo.SetParseDate(True)
  
  m.Logout()
  
  return message_infos

def ExtractThreads(message_infos):
  thread_messages = []
  for message_info in message_infos:
    thread_message = jwzthreading.make_message(message_info.headers)
    if thread_message:
      thread_message.message_info = message_info
      thread_messages.append(thread_message)
      
  thread_dict = jwzthreading.thread(thread_messages)
  
  containers = []
  for subject, container in thread_dict.items():
    # jwzthreading is too aggressive in threading by subject and will combine
    # distinct threads that happen to have the same subject. Split them up if
    # we have a dummy container that has lots of children at the first level.
    if container.is_dummy() and len(container.children) >= 10:
      for child_container in container.children:
        child_container.subject = subject
        containers.append(child_container)
    else:
      container.subject = subject
      containers.append(container)
    
  return containers

def InitStats(date_range):
  s = [
    stats.TitleStat(date_range, "All Mail"),
    stats.StatTabGroup(
      (
        "Time",
        stats.StatColumnGroup(
          stats.DayOfWeekStat(),
          stats.TimeOfDayStat(),
          stats.YearStat(date_range),
        ),
        stats.StatColumnGroup(
          stats.MonthStatCollection(date_range),
          stats.DayStatCollection(date_range),
        ),
      ),
      (
        "Size",
        stats.StatColumnGroup(
          stats.SizeBucketStat(),
          stats.SizeTableStat(),
        ),
      ),
      (
        "People and Lists",
        stats.StatColumnGroup(
          stats.SenderTableStat(),
          stats.RecipientTableStat(),
        ),
        stats.StatColumnGroup(
          stats.ListIdTableStat(),
        ),
      ),
      (
        "Threads",
        stats.StatColumnGroup(
          stats.ThreadSizeBucketStat(),
          stats.ThreadSizeTableStat(),
        ),
        stats.StatColumnGroup(
          stats.ThreadStarterTableStat(),
          stats.ThreadListTableStat(),
        )
      )
    )
  ]
  
  return s

logging.basicConfig(level=logging.DEBUG,
                    format="[%(asctime)s] %(message)s")

logging.info("Initializing")

opts = GetOptsMap()

message_infos = GetMessageInfos(opts)

logging.info("Extracting threads")
threads = ExtractThreads(message_infos)

stats = InitStats(messageinfo.MessageInfo.GetDateRange())

logging.info("Generating stats")
for stat in stats:
  stat.ProcessMessageInfos(message_infos, threads)

logging.info("Outputting HTML")

t = Template(
    file="templates/index.tmpl",
    searchList = {
      "stats": stats,
      "host": re.sub("^.*@", "", opts["username"])
    }
)
out = codecs.open("out/index.html", mode="w", encoding='utf-8')
out.write(unicode(t))
out.close()

logging.info("Done")