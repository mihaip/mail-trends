#!/usr/bin/python

# Simple program to take a directory from the Enron corpus 
# (http://www.cs.cmu.edu/~enron/) and generate an mbox file from it (in the
# Enron corpus, the messages are stored as individual files and don't begin
# with a From: line, but otherwise seem to be RFC 2822 messages)
#
# To run:
# ./enron.py directory_path
# The mbox file will be sent to stdout

import email
import os
import os.path
import sys

directory = sys.argv[1]

for root, dirs, file_names in os.walk(directory):
  for file_name in file_names:
    file_path = os.path.join(root, file_name)
    
    message_file = file(file_path, "r")
    message_text = message_file.read()
    message_file.close()
    
    msg = email.message_from_string(message_text)
    
    print msg.as_string(unixfrom=True)
    print ""