#!/usr/bin/python

import codecs
import getopt
import getpass
import logging
import messageinfo
import re
import sys

from Cheetah.Template import Template
import jwzthreading

import mail
import stats.base
import stats.bucket
import stats.group
import stats.table

def GetOptsMap():
  opts, args = getopt.getopt(sys.argv[1:], "", [
      # Standard options
      "username=", "password=", "use_ssl", "server=", 

      # Other params
      "filter_out=", "me=",
      
      # Development options
      "record", "replay", 
      "max_messages=", "random_subset",
      "skip_labels"])
  
  opts_map = {}
  for name, value in opts:
    opts_map[name[2:]] = value

  assert "username" in opts_map
  
  if "password" not in opts_map:
    opts_map["password"] = getpass.getpass(
        prompt="Password for %s: " % opts_map["username"])
  
  assert "password" in opts_map
  assert "server" in opts_map
  
  return opts_map

def GetMessageInfos(opts):
  m = mail.Mail(
      opts["server"], "use_ssl" in opts, opts["username"], opts["password"],
      "record" in opts, "replay" in opts, 
      "max_messages" in opts and int(opts["max_messages"]) or -1,
      "random_subset" in opts)
  
  # First, get all message infos
  m.SelectAllMail()
  
  message_infos = m.GetMessageInfos()
  
  # Filter out those that we're not interested in
  if "filter_out" in opts:
    message_infos = FilterMessageInfos(message_infos, opts["filter_out"])
  
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
  
  # Tag messages as being from the user running the script
  if "me" in opts:
    logging.info("Identifying \"me\" messages")
    me_addresses = [
        address.lower().strip() for address in opts["me"].split(",")]
    
    me_from_count = 0
    me_to_count = 0
    
    for message_info in message_infos:
      name, address = message_info.GetSender()
      
      for me_address in me_addresses:
        if me_address == address:
          message_info.is_from_me = True
          me_from_count += 1
          break
          
      for name, address in message_info.GetRecipients():
        for me_address in me_addresses:
          if me_address == address:
            message_info.is_to_me = True
            me_to_count += 1
            break
        if message_info.is_to_me: break
            
    logging.info("  %d messages are from \"me\"" % me_from_count)
    logging.info("  %d messages are to \"me\"" % me_to_count)
  
  m.Logout()
  
  return message_infos

def FilterMessageInfos(message_infos, filter_param):
  logging.info("Filtering messages")
  remaining_message_infos = []
  
  filters = []
  raw_filters = filter_param.split(",")
  for raw_filter in raw_filters:
    operator, value = raw_filter.strip().split(":", 1)
    filters.append([operator, value.lower()])
  
  for message_info in message_infos:
    filtered_out = False
    for operator, operator_value in filters:
      if operator == "to":
        pairs = message_info.GetRecipients()
      elif operator == "from":
        pairs = [message_info.GetSender()]
      elif operator == "list":
        pairs = [message_info.GetListId()]
      else:
        raise AssertionError("unknown operator: %s" % operator)

      values = [name and name.lower() or "" for name, address in pairs] + \
               [address and address.lower() or "" for name, address in pairs]

      for value in values:
        if value.find(operator_value) != -1:
          filtered_out = True
          break
      
      if filtered_out:
        break
    
    if not filtered_out:
      remaining_message_infos.append(message_info)

  logging.info("  %d messages remaining" % len(remaining_message_infos))
  return remaining_message_infos

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
    stats.base.TitleStat(date_range, "All Mail"),
    stats.group.StatTabGroup(
      (
        "Time",
        stats.group.StatColumnGroup(
          stats.bucket.DayOfWeekStat(),
          stats.bucket.TimeOfDayStat(),
          stats.bucket.YearStat(date_range),
        ),
        stats.group.StatColumnGroup(
          stats.group.MonthStatCollection(date_range),
          stats.group.DayStatCollection(date_range),
        ),
      ),
      (
        "Size",
        stats.group.StatColumnGroup(
          stats.bucket.SizeBucketStat(),
          stats.table.SizeTableStat(),
        ),
      ),
      (
        "People and Lists",
        stats.group.StatColumnGroup(
          stats.table.SenderTableStat(),
          stats.group.SenderDistributionStatCollection(date_range),
        ),
        stats.group.StatColumnGroup(
          stats.table.RecipientTableStat(),
          stats.group.RecipientDistributionStatCollection(date_range),
        ),
        stats.group.StatColumnGroup(
          stats.table.ListIdTableStat(),
          stats.group.ListDistributionStatCollection(date_range),
        ),
      ),
      (
        "Me",
        stats.group.StatColumnGroup(
          stats.table.MeRecipientTableStat(),
        ),
        stats.group.StatColumnGroup(
          stats.table.MeSenderTableStat(),
        ),
      ),
      (
        "Threads",
        stats.group.StatColumnGroup(
          stats.bucket.ThreadSizeBucketStat(),
          stats.table.ThreadSizeTableStat(),
        ),
        stats.group.StatColumnGroup(
          stats.table.ThreadStarterTableStat(),
          stats.table.ThreadListTableStat(),
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