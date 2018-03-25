#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
http://sametmax.com/ecrire-des-logs-en-python/
https://docs.python.org/3/library/time.html#time.strftime

use logging package for salometools

handler:
  on info() no format
  on other formatted indented on multi lines messages
"""

import os
import sys
import logging
import pprint as PP

_verbose = False
_name = "loggingSat"

def indent(msg, nb, car=" "):
  """indent nb car (spaces) multi lines message except first one"""
  s = msg.split("\n")
  res = ("\n"+car*nb).join(s)
  return res

def log(msg):
  """elementary log when no logger yet"""
  prefix = "%s.log: " % _name
  nb = len(prefix)
  if _verbose: print(prefix + indent(msg, nb))

log("import logging on %s" % logging.__file__)

_loggerDefaultName = 'SatDefaultLogger'
_loggerUnittestName = 'SatUnittestLogger'

def getDefaultLogger():
  log("getDefaultLogger %s" % _loggerDefaultName)
  return logging.getLogger(_loggerDefaultName)

def getUnittestLogger():
  log("getUnittestLogger %s" % _loggerUnittestName)
  return logging.getLogger(_loggerUnittestName)

def dirLogger(logger):
  logger.info('dir(logger name=%s):\n' % logger.name + PP.pformat(dir(logger)))

_loggerDefault = getDefaultLogger()
_loggerUnittest = getUnittestLogger()


class DefaultFormatter(logging.Formatter):
  def format(self, record):
    # print "", record.levelname #type(record), dir(record)
    if record.levelname == "INFO": 
      return str(record.msg)
    else:
      return indent(super(DefaultFormatter, self).format(record), 12)

class UnittestFormatter(logging.Formatter):
  def format(self, record):
    # print "", record.levelname #type(record), dir(record)
    nb = len("2018-03-17 12:15:41 :: INFO     :: ")
    return indent(super(UnittestFormatter, self).format(record), nb)


class UnittestStream(object):
  """
  write my stream class
  only write and flush are used for the streaming
  https://docs.python.org/2/library/logging.handlers.html
  https://stackoverflow.com/questions/31999627/storing-logger-messages-in-a-string
  """
  def __init__(self):
    self.logs = ''

  def write(self, astr):
    # log("UnittestStream.write('%s')" % astr)
    self.logs += astr

  def flush(self):
    pass

  def __str__(self):
    return self.logs


def initLoggerAsDefault(logger, fmt=None, level=None):
  """
  init logger as prefixed message and indented message if multi line
  exept info() outed 'as it' without any format
  """
  log("initLoggerAsDefault name=%s\nfmt='%s' level='%s'" % (logger.name, fmt, level))
  handler = logging.StreamHandler() # Logging vers console
  if fmt is not None:
    # formatter = logging.Formatter(fmt, "%Y-%m-%d %H:%M:%S")
    formatter = DefaultFormatter(fmt, "%y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
  logger.addHandler(handler)
  if level is not None:
    logger.setLevel(level)
  else:
    logger.setLevel(logger.INFO)

  
def initLoggerAsUnittest(logger, fmt=None, level=None):
  """
  init logger as silent on stdout/stderr
  used for retrieve messages in memory for post execution unittest
  https://docs.python.org/2/library/logging.handlers.html
  """
  log("initLoggerAsUnittest name=%s\nfmt='%s' level='%s'" % (logger.name, fmt, level))
  stream = UnittestStream()
  handler = logging.StreamHandler(stream) # Logging vers stream
  if fmt is not None:
    # formatter = logging.Formatter(fmt, "%Y-%m-%d %H:%M:%S")
    formatter = UnittestFormatter(fmt, "%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
  logger.addHandler(handler)
  logger.streamUnittest = stream
  if level is not None:
    logger.setLevel(level)
  else:
    logger.setLevel(logger.DEBUG)

  
def testLogger_1(logger):
  """small test"""
  # dirLogger(logger)
  logger.debug('test logger debug')
  logger.info('test logger info')
  logger.warning('test logger warning')
  logger.error('test logger error')
  logger.critical('test logger critical')
  logger.info('test logger info:\n- second line\n- third line')
  logger.warning('test logger warning:\n- second line\n- third line')

  
if __name__ == "__main__":
  print("\n**** DEFAULT")
  logdef = getDefaultLogger()
  initLoggerAsDefault(logdef, '%(levelname)-8s :: %(message)s', level=logging.INFO)
  testLogger_1(logdef)
  print("\n**** UNITTEST")
  loguni = getUnittestLogger()
  initLoggerAsUnittest(loguni, '%(asctime)s :: %(levelname)-8s :: %(message)s', level=logging.DEBUG)
  testLogger_1(loguni) # is silent
  # log("loguni.streamUnittest:\n%s" % loguni.streamUnittest)
  print("loguni.streamUnittest:\n%s" % loguni.streamUnittest)
  
  from colorama import Fore as FG
  from colorama import Style as ST
  print("this is %scolored%s!" % (FG.G))
  