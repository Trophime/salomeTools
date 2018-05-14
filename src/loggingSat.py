#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
salomeTools logger. using logging package
 
| http://sametmax.com/ecrire-des-logs-en-python/
| 
| Define two LoggerSat instances in salomeTools, no more need.
|   - _loggerDefault as production/development logger
|   - _loggerUnittest as unittest logger
|
| see use of handlers of _loggerDefault for
| log console and log files xml, txt
|
| console handler:
|   - info() : no format
|   - error() warning() trace() debug() etc. :
|      formatted indented on multi lines messages using handlers
|
| file handlers:
|   - info() error() warning() trace() debug() etc. :
|      formatted indented on multi lines messages using handlers
"""

import os
import sys
import logging as LOGI
import pprint as PP
import src.coloringSat as COLS

_verbose = False
_name = "loggingSat"
_loggerDefaultName = 'SatDefaultLogger'
_loggerUnittestName = 'SatUnittestLogger'


def indent(msg, nb, car=" "):
  """indent nb car (spaces) multi lines message except first one"""
  s = msg.split("\n")
  res = ("\n"+car*nb).join(s)
  return res

def indentUnittest(msg, prefix=" | "):
  """
  indent multi lines message except first one with prefix.
  prefix default is designed for less spaces for size logs files
  and keep logs human eye readable
  """
  s = msg.split("\n")
  res = ("\n" + prefix).join(s)
  return res

def log(msg):
  """elementary log when no logging.Logger yet"""
  prefix = "%s.log: " % _name
  nb = len(prefix)
  if _verbose: print(prefix + indent(msg, nb))


log("import logging on %s" % LOGI.__file__)


def dirLogger(logger):
  logger.info('dir(logger name=%s):\n' % logger.name, PP.pformat(dir(logger)))


class LoggerSat(LOGI.Logger):
  """
  inherited class logging.Logger for logger salomeTools
  
  | add a level TRACE as log.trace(msg) 
  | below log.info(msg)
  | above log.debug(msg)
  | to assume store long log asci in files txt under/outside files xml
  | 
  | see: /usr/lib64/python2.7/logging/__init__.py etc.
  """
  
  _TRACE = LOGI.INFO - 2 # just below
  
  def __init__(self, name, level=LOGI.INFO):
    """
    Initialize the logger with a name and an optional level.
    """
    super(LoggerSat, self).__init__(name, level)
    LOGI.addLevelName(self._TRACE, "TRACE")
    # LOGI.TRACE = self._TRACE # only for coherency,
    
  def trace(self, msg, *args, **kwargs):
    """
    Log 'msg % args' with severity '_TRACE'.

    To pass exception information, use the keyword argument exc_info with
    a true value, e.g.

    logger.trace("Houston, we have a %s", "long trace to follow")
    """
    if self.isEnabledFor(self._TRACE):
        self._log(self._TRACE, msg, args, **kwargs)

  def isEnabledFor(self, level):
    """
    Is this logger enabled for level 'level'?
    currently not modified from logging.Logger class
    """
    log("logger %s isEnabledFor %i>=%i" % (self.name, level, self.getEffectiveLevel()))
    if self.manager.disable >= level:
        return 0
    return level >= self.getEffectiveLevel()

class DefaultFormatter(LOGI.Formatter):
  
  # to set color prefix, problem with indent format as 
  _ColorLevelname = {
    "DEBUG": "<green>",
    "TRACE": "<green>",
    "INFO":  "<green>",
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
    """
    set color implies color special characters and
    tabulate levelname length of string
    """
    color = self._ColorLevelname[levelname]
    res = color + levelname + "<reset>"
    nb = len(levelname)
    res = res + " "*(8-nb) # 8 as len("CRITICAL")
    # print "'%s'" % res
    return res


class UnittestFormatter(LOGI.Formatter):
  def format(self, record):
    # print "", record.levelname #type(record), dir(record)
    # nb = len("2018-03-17 12:15:41 :: INFO     :: ")
    res = super(UnittestFormatter, self).format(record)
    res = indentUnittest(res)
    return COLS.toColor(res)


class UnittestStream(object):
  """
  write my stream class
  only write and flush are used for the streaming
  
  | https://docs.python.org/2/library/logging.handlers.html
  | https://stackoverflow.com/questions/31999627/storing-logger-messages-in-a-string
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
    """final method called when message is logged"""
    # log("UnittestStream.write('%s')" % astr) # for debug ... 
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
  handler = LOGI.StreamHandler(sys.stdout) # Logging vers console
  if fmt is not None:
    # formatter = LOGI.Formatter(fmt, "%Y-%m-%d %H:%M:%S")
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
  handler = LOGI.StreamHandler(stream) # Logging vers stream
  if fmt is not None:
    # formatter = LOGI.Formatter(fmt, "%Y-%m-%d %H:%M:%S")
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

def setFileHandler(logger, config):
  """
  add file handler to logger to set log files
  for salometools command. 
  when command is known from pyconf/config instance
  
  | Example: 
  | log files names for command prepare 
  | with micro commands clean/source/patch
  |   ~/LOGS/20180510_140606_prepare_lenovo.xml
  |   ~/LOGS/OUT/20180510_140606_prepare_lenovo.txt
  |   ~/LOGS/micro_20180510_140607_clean_lenovo.xml
  |   ~/LOGS/OUT/micro_20180510_140607_clean_lenovo.txt
  |   etc.
  """
  import src.debug as DBG # avoid cross import
  DBG.write("setFileHandler", logger.handlers, True)
  DBG.write("setFileHandler", config.VARS, True)
  
def getDefaultLogger():
  log("getDefaultLogger %s" % _loggerDefaultName)
  # case multithread may be problem as not LOGI._acquireLock()
  previousClass = LOGI._loggerClass
  LOGI.setLoggerClass(LoggerSat) # to get LoggerSat instance with trace etc.
  res = LOGI.getLogger(_loggerDefaultName)
  LOGI.setLoggerClass(previousClass)
  return res

def getUnittestLogger():
  log("getUnittestLogger %s" % _loggerUnittestName)
  # case multithread may be problem as not LOGI._acquireLock()
  previousClass = LOGI._loggerClass
  LOGI.setLoggerClass(LoggerSat) # to get LoggerSat instance with trace etc.
  res = LOGI.getLogger(_loggerUnittestName)
  LOGI.setLoggerClass(previousClass)
  return res
  
def testLogger_1(logger):
  """small test"""
  # dirLogger(logger)
  logger.debug('test logger debug')
  logger.trace('test logger trace')
  logger.info('test logger info')
  logger.warning('test logger warning')
  logger.error('test logger error')
  logger.critical('test logger critical')
  logger.info('\ntest logger info: no indent\n- second line\n- third line\n')
  logger.warning('test logger warning:\n- second line\n- third line')

def testMain():
  print("\n**** DEFAULT logger")
  logdef = getDefaultLogger()
  # use of setColorLevelname <color>...<reset>, so do not use %(levelname)-8s
  initLoggerAsDefault(logdef, '%(levelname)s :: %(message)s', level=LOGI.DEBUG)
  testLogger_1(logdef)
  print("\n**** UNITTEST logger")
  loguni = getUnittestLogger()
  initLoggerAsUnittest(loguni, '%(asctime)s :: %(levelname)-8s :: %(message)s', level=LOGI.DEBUG)
  testLogger_1(loguni) # is silent
  # log("loguni.getLogs():\n%s" % loguni.getLogs())
  print("loguni.streamUnittest:\n%s" % loguni.getLogs())
  
  from colorama import Fore as FG
  from colorama import Style as ST
  print("this is unconditionally %scolored in green%s !!!" % (FG.GREEN, ST.RESET_ALL))   

if __name__ == "__main__":
  # get path to salomeTools sources
  satdir = os.path.dirname(os.path.dirname(__file__))
  # Make the src & commands package accessible from all code
  sys.path.insert(0, satdir)
  testMain()  
else:
  # get two LoggerSat instance used in salomeTools, no more needed.
  _loggerDefault = getDefaultLogger()
  _loggerUnittest = getUnittestLogger()
  initLoggerAsDefault(_loggerDefault, '%(levelname)s :: %(message)s', level=LOGI.INFO)
  initLoggerAsUnittest(_loggerUnittest, '%(asctime)s :: %(levelname)s :: %(message)s', level=LOGI.DEBUG)
