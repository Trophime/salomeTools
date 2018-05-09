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
import src.coloringSat as COLS

_verbose = False
_name = "loggingSat"

def indent(msg, nb, car=" "):
  """indent nb car (spaces) multi lines message except first one"""
  s = msg.split("\n")
  res = ("\n"+car*nb).join(s)
  return res

def indentUnittest(msg, prefix=" | "):
  """
  indent car multi lines message except first one
  car default is less spaces for size logs files
  keep human readable
  """
  s = msg.split("\n")
  res = ("\n" + prefix).join(s)
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
  
  # to set color prefix, problem with indent format
  _ColorLevelname = {
    "DEBUG": "<green>",
    "INFO": "<green>",
    "WARNING": "<red>",
    "ERROR": "<yellow>",
    "CRITICAL": "<yellow>",
  }
  
  def format(self, record):
    if _verbose:
      import src.debug as DBG # avoid cross import
      DBG.write("DefaultFormatter.format", "%s: %s..." % (record.levelname, record.msg[0:20]), True)
    record.levelname = self.setColorLevelname(record.levelname)
    if "INFO" in record.levelname:
      res = str(record.msg)
    else:
      res = indent(super(DefaultFormatter, self).format(record), 12)
    return COLS.toColor(res)
  
  def setColorLevelname(self, levelname):
    return self._ColorLevelname[levelname] + levelname + "<reset>"


class UnittestFormatter(logging.Formatter):
  def format(self, record):
    # print "", record.levelname #type(record), dir(record)
    # nb = len("2018-03-17 12:15:41 :: INFO     :: ")
    res = indentUnittest(super(UnittestFormatter, self).format(record), " | ")
    return COLS.toColor(res)


class UnittestStream(object):
  """
  write my stream class
  only write and flush are used for the streaming
  https://docs.python.org/2/library/logging.handlers.html
  https://stackoverflow.com/questions/31999627/storing-logger-messages-in-a-string
  """
  def __init__(self):
    self._logs = ''
    
  def getLogs(self):
    return self._logs
  
  def getLogsAndClear(self):
    res = self._logs
    self._logs = ''
    return res

  def write(self, astr):
    # log("UnittestStream.write('%s')" % astr)
    self._logs += astr

  def flush(self):
    pass

  def __str__(self):
    return self._logs


def initLoggerAsDefault(logger, fmt=None, level=None):
  """
  init logger as prefixed message and indented message if multi line
  exept info() outed 'as it' without any format
  """
  log("initLoggerAsDefault name=%s\nfmt='%s' level='%s'" % (logger.name, fmt, level))
  handler = logging.StreamHandler(sys.stdout) # Logging vers console
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
  logger.stream = stream
  logger.getLogs = stream.getLogs
  logger.getLogsAndClear = stream.getLogsAndClear
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
  logger.info('\ntest logger info: no indent\n- second line\n- third line\n')
  logger.warning('test logger warning:\n- second line\n- third line')

  
if __name__ == "__main__":
  print("\n**** DEFAULT logger")
  logdef = getDefaultLogger()
  # problem if add +2? if append 2 setColorLevelname <color><reset>, not fixed
  initLoggerAsDefault(logdef, '%(levelname)-8s :: %(message)s', level=logging.INFO)
  testLogger_1(logdef)
  print("\n**** UNITTEST logger")
  loguni = getUnittestLogger()
  initLoggerAsUnittest(loguni, '%(asctime)s :: %(levelname)-8s :: %(message)s', level=logging.DEBUG)
  testLogger_1(loguni) # is silent
  # log("loguni.streamUnittest:\n%s" % loguni.streamUnittest)
  print("loguni.streamUnittest:\n%s" % loguni.streamUnittest)
  
  from colorama import Fore as FG
  from colorama import Style as ST
  print("this is %scolored in green%s !!!" % (FG.GREEN, ST.RESET_ALL))
  
else:  
  _loggerDefault = getDefaultLogger()
  _loggerUnittest = getUnittestLogger()
  initLoggerAsDefault(_loggerDefault, '%(levelname)-8s :: %(message)s', level=logging.INFO)
  initLoggerAsUnittest(_loggerUnittest, '%(asctime)s :: %(levelname)-8s :: %(message)s', level=logging.DEBUG)
