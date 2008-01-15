#!/usr/local/bin/python

import getopt
import logging
import messageinfo
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
  thread_messages = [jwzthreading.make_message(m.headers) for m in message_infos]
  thread_dict = jwzthreading.thread(thread_messages)
  
  containers = []
  for subject, container in thread_dict.items():
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
          stats.DayOfWeekStat("All Mail"),
          stats.TimeOfDayStat("All Mail"),
          stats.YearStat(date_range, "All Mail"),
        ),
        stats.StatColumnGroup(
          stats.MonthStatCollection(date_range, "All Mail"),
          stats.DayStatCollection(date_range, "All Mail"),
        ),
      ),
      (
        "Size",
        stats.StatColumnGroup(
          stats.SizeBucketStat("All Mail"),
          stats.SizeTableStat("All Mail"),
        ),
      ),
      (
        "People and Lists",
        stats.StatColumnGroup(
          stats.SenderTableStat("All Mail"),
          stats.RecipientTableStat("All Mail"),
        ),
        stats.StatColumnGroup(
          stats.ListIdTableStat("All Mail"),
        ),
      ),
      (
        "Threads",
        stats.StatColumnGroup(
          stats.ThreadSizeBucketStat("All Mail"),
          stats.ThreadSizeTableStat("All Mail"),
        ),
      )
    )
  ]
  
  return s

logging.basicConfig(level=logging.DEBUG,
                    format="[%(asctime)s] %(message)s")

logging.info("Initializing")

opts = GetOptsMap()

message_infos = GetMessageInfos(opts)

threads = ExtractThreads(message_infos)

stats = InitStats(messageinfo.MessageInfo.GetDateRange())

logging.info("Generating stats")
for stat in stats:
  stat.ProcessMessageInfos(message_infos, threads)

logging.info("Outputting HTML")

t = Template(file="templates/index.tmpl", searchList = {"stats": stats})
out = open("out/index.html", "w")
out.write(str(t))
out.close()

logging.info("Done")