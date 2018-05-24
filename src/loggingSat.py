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
|
| WARNING:
|  log step are present in xml 'command's internal traces' (which exclude info for resume concision)
|  log trace are present in xml 'output log' (as result of verbose subprocess make etc)
"""

"""
# to launch examples:

export TRG=SALOME-8.4.0
cd .../sat5.1
src/loggingSat.py
AllTestLauncherSat.py -p 'test_???_logging*.py'
export TRG=SALOME-8.4.0
sat config $TRG -i KERNEL
sat config -v LOCAL.log_dir
sat config $TRG -n -v LOCAL.log_dir
rm -rf /volatile/wambeke/SAT5/SAT5_S840_MATIX24/LOGS
sat prepare $TRG -p KERNEL
sat log

rm -rf TMP
sat prepare $TRG -p KERNEL
more TMP/*xml TMP/OUT/*.txt
"""

import os
import sys
import time
import logging as LOGI
from logging.handlers import BufferingHandler
import pprint as PP


_verbose = False
_name = "loggingSat"
_loggerDefaultName = 'SatDefaultLogger'
_loggerUnittestName = 'SatUnittestLogger'

_STEP = LOGI.INFO - 1 # step level is just below INFO
_TRACE = LOGI.INFO - 2 # trace level is just below STEP

LOGI.STEP = _STEP # only for coherency,
LOGI.TRACE = _TRACE # only for coherency,


#################################################################
# utilities methods
#################################################################

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

def log(msg, force=False):
  """elementary log when no logging.Logger yet"""
  prefix = "---- %s.log: " % _name
  nb = len(prefix)
  if _verbose or force:
    print(prefix + indent(msg, nb))

# just for debug info where is import logging
log("import logging on %s" % LOGI.__file__)


def getStrDirLogger(logger):
  """
  Returns multi line string for logger description, with dir(logger).
  Used for debug
  """
  lgr = logger # shortcut
  msg = "%s(name=%s, dateLogger=%s):\n%s\n"
  cName = lgr.__class__.__name__
  res = msg % (cName, lgr.name, lgr.dateLogger, PP.pformat(dir(lgr)))
  return res

def getStrHandler(handler):
  """
  Returns one line string for handler description 
  (as inexisting __repr__)
  to avoid create inherited classe(s) handler
  """ 
  h = handler # shortcut
  msg = "%s(name=%s)"
  cName = h.__class__.__name__
  res = msg % (cName, h.get_name())
  return res
  
def getStrShort(msg):
  """Returns short string for msg (as first caracters without line feed"""
  # log("getStrShort " + str(msg), True)
  res = msg.replace("\n", "//")[0:30]
  return res
  
def getStrLogRecord(logRecord):
  """
  Returns one line string for simple logging LogRecord description 
  """
  import src.coloringSat as COLS # needs sys.path.insert(0, satdir)
  msg = "LogRecord(level='%s', msg='%s...')"
  shortMsg = getStrShort(logRecord.msg)
  levelName = COLS.cleanColors(logRecord.levelname).replace(" ", "")
  res = msg % (levelName, shortMsg)
  return res

def getListOfStrLogRecord(listOfLogRecord):
  """
  Returns one line string for logging LogRecord description 
  """ 
  res = [getStrLogRecord(l) for l in listOfLogRecord]
  return res

#################################################################
# salometools logger classes
#################################################################

try:
    unicode
    _unicode = True
except NameError:
    _unicode = False

def getMessage(self):
    """
    modified from logging.__init__.LogRecord.getMessage, 
    better message on format error 
    Return the message for this LogRecord.
  
    Return the message for this LogRecord after merging any user-supplied
    arguments with the message.
    """
    if not _unicode: #if no unicode support...
        msg = str(self.msg)
    else:
        msg = self.msg
        if not isinstance(msg, basestring):
            try:
                msg = str(self.msg)
            except UnicodeError:
                msg = self.msg      #Defer encoding till later
    if self.args:
        try: # better message on format error 
          msg = msg % self.args
        except Exception as e:
          msg = "ERROR: %s with args %s" % (msg, PP.pformat(self.args))
          log(msg, True)
    return msg

LOGI.LogRecord.getMessage = getMessage # better message if error

#################################################################
class LoggerSat(LOGI.Logger):
  """
  Inherited class logging.Logger for logger salomeTools
  
  | add a level STEP as log.step(msg) 
  | add a level TRACE as log.trace(msg) 
  | below log.info(msg)
  | above log.debug(msg)
  | to assume message step inside files xml 'command's internal traces'
  | to assume store long log asci in files txt outside files xml
  | 
  | see: /usr/lib64/python2.7/logging/__init__.py etc.
  """
  
  def __init__(self, name, level=LOGI.INFO):
    """
    Initialize the logger with a name and an optional level.
    """
    super(LoggerSat, self).__init__(name, level)
    LOGI.addLevelName(_STEP, "STEP")
    LOGI.addLevelName(_TRACE, "TRACE")
    self.dateLogger = "NoDateLogger"
    self.isClosed = False
    self.idCommandHandlers = 0 # incremented, 0 for main command 1, 2, etc. for micro command
    self.STEP = _STEP
    self.TRACE = _TRACE
    
  def close(self):
    """
    final stuff for logger, done at end salomeTools
    flushed and closed xml files have to be not overriden/appended
    """
    if self.isClosed: 
      raise Exception("logger closed yet: %s" % self)
    log("close stuff logger %s" % self) # getStrDirLogger(self)
    for handl in list(self.handlers):  # get original list
      log("close stuff handler %s" % getStrHandler(handl))
      handl.close() # Tidy up any resources used by the handler.
      self.removeHandler(handl)
    # todo etc
    self.isClosed = True # done at end sat, flushed closed xml files.
    return
    
  def __repr__(self):
    """one line string representation"""
    msg = "%s(name=%s, dateLogger=%s, handlers=%s)"
    cName = self.__class__.__name__
    h = [getStrHandler(h) for h in self.handlers]
    h = "[" + ", ".join(h) + "]"
    res = msg % (cName, self.name, self.dateLogger, h)
    return res
    
  def trace(self, msg, *args, **kwargs):
    """
    Log 'msg % args' with severity '_TRACE'.
    """
    log("trace stuff logger '%s' msg '%s...'" % (self.name, getStrShort(msg)))
    if self.isEnabledFor(_TRACE):
        self._log(_TRACE, msg, args, **kwargs)

  def step(self, msg, *args, **kwargs):
    """
    Log 'msg % args' with severity '_STEP'.
    """
    log("step stuff logger '%s' msg '%s...'" % (self.name, getStrShort(msg)))
    if self.isEnabledFor(_STEP):
        self._log(_STEP, msg, args, **kwargs)

  def xx_isEnabledFor(self, level):
    """
    Is this logger enabled for level 'level'?
    currently not modified from logging.Logger class,
    here only for call log debug.
    """
    log("logger %s isEnabledFor %i>=%i" % (self.name, level, self.getEffectiveLevel()))
    if self.manager.disable >= level:
        return 0
    return level >= self.getEffectiveLevel()

  def setFileHandlerForCommand(self, cmdParent, cmdInstance):
    """
    add file handler to logger to set log files
    for a salometools command. 
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
    import src.utilsSat as UTS # needs sys.path.insert(0, satdir)

    logger = self
    config = cmdInstance.getConfig()
    
    #import src.debug as DBG # avoid cross import
    log("setFileHandler %s" % logger)
    log("setFileHandler config\n%s" % PP.pformat(dict(config.VARS)))
    log("setFileHandler TODO set log_dir config.LOCAL.log_dir")
    
    log_dir = "TMP" # TODO for debug config.LOCAL.log_dir # files xml
    log_dir_out = os.path.join(log_dir, "OUT") # files txt
    UTS.ensure_path_exists(log_dir)
    UTS.ensure_path_exists(log_dir_out)
    datehour = config.VARS.datehour
    cmd = config.VARS.command
    fullNameCmd = cmdInstance.getFullNameStr()
    hostname = config.VARS.hostname
    nameFileXml = "%s_%02i_%s_%s.xml" % (datehour, self.idCommandHandlers, cmd, hostname)
    nameFileTxt = "%s_%02i_%s_%s.txt" % (datehour, self.idCommandHandlers, cmd, hostname)
    fileXml = os.path.join(log_dir, nameFileXml)
    fileTxt = os.path.join(log_dir_out, nameFileTxt)
    
    # precaution
    lastCmd = cmdInstance.getFullNameList()[-1]
    if cmd != lastCmd:
      msg = "setFileHandler '%s' command name incoherency in config '%s'" % (fullNameCmd, cmd)
      logger.critical(msg)
  
    nbhandl = len(logger.handlers) # number of active current handlers
    
    if self.idCommandHandlers == 0: # first main command
      log("setFileHandler '%s' main command (id=%i)" % (fullNameCmd, self.idCommandHandlers))
      
      ################################
      # Logging vers file xml
      handler = XmlHandler(3000) # no many log outputs in memory
      handler.setLevel(LOGI.STEP)
      handler.set_name(nameFileXml)
      handler.set_target_file(fileXml)
      handler.set_config(config)
      handler.idCommandHandlers = self.idCommandHandlers
      
      fmt = '%(asctime)s :: %(levelname)-8s :: %(message)s'
      formatter = FileXmlFormatter(fmt, "%y-%m-%d %H:%M:%S")
      
      handler.setFormatter(formatter)
      logger.addHandler(handler)
      
      ################################
      # Logging vers file txt
      handler = LOGI.FileHandler(fileTxt)
      handler.setLevel(LOGI.TRACE)
      handler.set_name(nameFileTxt)
      handler.idCommandHandlers = self.idCommandHandlers
      
      fmt = '%(asctime)s :: %(levelname)-8s :: %(message)s'
      formatter = FileTxtFormatter(fmt, "%y-%m-%d %H:%M:%S")
      
      handler.setFormatter(formatter)
      logger.addHandler(handler)
      
  
    elif self.idCommandHandlers > 0: # secondary micro command
      log("TODO setFileHandler '%s' micro command (id=%i)" % (fullNameCmd, self.idCommandHandlers))
      
      ################################
      # Logging vers file xml
      handler = XmlHandler(3000) # no many log outputs in memory
      handler.setLevel(LOGI.STEP)
      handler.set_name(nameFileXml)
      handler.set_target_file(fileXml)
      handler.set_config(config)
      handler.idCommandHandlers = self.idCommandHandlers
      
      fmt = '%(asctime)s :: %(levelname)-8s :: %(message)s'
      formatter = FileXmlFormatter(fmt, "%y-%m-%d %H:%M:%S")
      
      handler.setFormatter(formatter)
      logger.addHandler(handler)
      
      ################################
      # Logging vers file txt
      handler = LOGI.FileHandler(fileTxt)
      handler.setLevel(LOGI.TRACE)
      handler.set_name(nameFileTxt)
      handler.idCommandHandlers = self.idCommandHandlers
      
      fmt = '%(asctime)s :: %(levelname)-8s :: %(message)s'
      formatter = FileTxtFormatter(fmt, "%y-%m-%d %H:%M:%S")
      
      handler.setFormatter(formatter)
      logger.addHandler(handler)
    
    cmdInstance.setIdCommandHandlers(self.idCommandHandlers)
    newLink = self.initLinkForCommand(cmdParent, cmdInstance)
    newLink.setAuthAttr("cmd_name", cmd)
    newLink.setAuthAttr("log_file_name", nameFileXml)
    
    self.idCommandHandlers += 1
    log("setFileHandler %s" % logger)
    return self.idCommandHandlers
  
  def closeFileHandlerForCommand(self, cmdInstance):
    for handl in list(self.handlers): # get original list
      try: # may be foreign handlers without idCommandHandlers attribute
        if handl.idCommandHandlers == cmdInstance._idCommandHandlers:
          nbini = len(self.handlers)
          log("close stuff handler %s" % getStrHandler(handl))
          handl.close() # Tidy up any resources used by the handler.
          self.removeHandler(handl)
          if len(self.handlers) != nbini-1:
            self.critical("Unexpected len(logger.handlers)=%i" %  len(self.handlers))
      except:
        self.warning("Existing logger handler without idCommandHandlers attribute %s" % str(handl))
        pass
      
  def initLinkForCommand(self, cmdParent, cmdNew):
    import src.linksXml as LIXML
    newLink = LIXML.appendLinkForCommand(cmdParent, cmdNew)
    return newLink
      
  def testNoReturn(self):
    """test when message ending '...' and level info then no return mode"""
    testNoReturn(self) # module method
  
#################################################################
class DefaultFormatter(LOGI.Formatter):
  
  # to set color prefix, problem with indent format as 
  _ColorLevelname = {
    "DEBUG": "<green>",
    "TRACE": "<green>",
    "STEP": "<green>",
    "INFO":  "<green>",
    "WARNING": "<red>",
    "ERROR": "<yellow>",
    "CRITICAL": "<yellow>",
  }
  
  def format(self, record):
    import src.coloringSat as COLS # needs sys.path.insert(0, satdir)
    if _verbose:
      import src.debug as DBG # avoid cross import
      DBG.write("DefaultFormatter.format", "%s: %s..." % (record.levelname, record.msg[0:20]), True)
    record.levelname = self.setColorLevelname(record.levelname)
    if "INFO" in record.levelname:
      res = str(record.msg)
    else:
      res = indent(super(DefaultFormatter, self).format(record), 12)
    res = COLS.toColor(res)
    # print "bbegin'%s'eend" % res
    return res
  
  def setColorLevelname(self, levelname):
    """
    set color implies color special characters and
    tabulate levelname length of string
    """
    color = self._ColorLevelname[levelname]
    res = color + levelname + "<reset>"
    nb = len(levelname)
    res = res + " "*(8-nb) # 8 as len("CRITICAL")
    # log("setColorLevelname'%s'" % res)
    return res


#################################################################
class UnittestFormatter(LOGI.Formatter):
  def format(self, record):
    import src.coloringSat as COLS # needs sys.path.insert(0, satdir)
    # print "", record.levelname #type(record), dir(record)
    # nb = len("2018-03-17 12:15:41 :: INFO     :: ")
    res = super(UnittestFormatter, self).format(record)
    res = indentUnittest(res)
    return COLS.toColor(res)


#################################################################
class FileTxtFormatter(LOGI.Formatter):
  def format(self, record):
    import src.coloringSat as COLS # needs sys.path.insert(0, satdir)
    # print "", record.levelname #type(record), dir(record)
    # nb = len("2018-03-17 12:15:41 :: INFO     :: ")
    res = super(FileTxtFormatter, self).format(record)
    res = indentUnittest(res)
    return COLS.cleanColors(res)


#################################################################
class FileXmlFormatter(LOGI.Formatter):
  def format(self, record):
    import src.coloringSat as COLS # needs sys.path.insert(0, satdir)
    # print "", record.levelname #type(record), dir(record)
    # nb = len("2018-03-17 12:15:41 :: INFO     :: ")
    res = super(FileXmlFormatter, self).format(record)
    res = indentUnittest(res)
    return COLS.cleanColors(res)


#################################################################
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

#################################################################
class StreamHandlerSat(LOGI.StreamHandler):
    """
    A handler class which writes logging records, appropriately formatted,
    to a stream. Note that this class does not close the stream, as
    sys.stdout or sys.stderr may be used.
    
    from logging.StreamHandler class,
    modified for 'no return' mode line if '...' at end of record message
    """
    def isLastRecordHaveNoReturn(self):
        """
        to memorize if last info record is 'no return' mode (as ending '...')
        avoid define inherited __init__
        """
        if not hasattr(self, "lastRecordHaveNoReturn"):
          self.lastRecordHaveNoReturn = False
        return self.lastRecordHaveNoReturn
      
    def isNeedFirstReturn(self, record):
        """
        'no return' mode  valid only if 2 consecutives info messages
        if not, needs insert return line BEFORE (warning, debug, or other) 
        current record message
        """
        if not self.isLastRecordHaveNoReturn(): 
          return False
        if record.levelno == LOGI.INFO:
          return False # case is 2 consecutives info messages (OK for continuity)
        return True # case need insert return line BEFORE message (KO for continuity)
          
    def emit(self, record):
        """
        Emit a record.

        If a formatter is specified, it is used to format the record.
        The record is then written to the stream with a trailing newline.  If
        exception information is present, it is formatted using
        traceback.print_exception and appended to the stream.  If the stream
        has an 'encoding' attribute, it is used to determine how to do the
        output to the stream.
        """
        try:
            msg = self.format(record)
            stream = self.stream
            if msg[-3:] == "..." and record.levelno == LOGI.INFO:
              fs = '%s'
              ufs = u'%s'
              self.lastRecordHaveNoReturn = True
            else:
              if self.isNeedFirstReturn(record):
                fs = '\n%s\n'
                ufs = u'\n%s\n'
                self.lastRecordHaveNoReturn = False
              else:
                fs = '%s\n'
                ufs = u'%s\n'
            if not _unicode: #if no unicode support...
                stream.write(fs % msg)
            else:
                try:
                    if (isinstance(msg, unicode) and
                        getattr(stream, 'encoding', None)):
                        # ufs = u'%s\n'
                        try:
                            stream.write(ufs % msg)
                        except UnicodeEncodeError:
                            #Printing to terminals sometimes fails. For example,
                            #with an encoding of 'cp1251', the above write will
                            #work if written to a stream opened or wrapped by
                            #the codecs module, but fail when writing to a
                            #terminal even when the codepage is set to cp1251.
                            #An extra encoding step seems to be needed.
                            stream.write((ufs % msg).encode(stream.encoding))
                    else:
                        stream.write(fs % msg)
                except UnicodeError:
                    stream.write(fs % msg.encode("UTF-8"))
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)
            
#################################################################
class XmlHandler(BufferingHandler):
  """
  log outputs in memory as BufferingHandler.
  Write ElementTree in file and flush are done once 
  when method close is called, to generate xml file.
  
  | atts = {
  |   "fileName": xml file name of micro command
  |   "command": cmd, # 'compile' or 'prepare' etc.
  |   "passed": res, # 'O' or '1'
  |   "launchedCommand" : fullcmd, # 'compile TOTO -etc'
  |   }
  |
  | see: https://docs.python.org/2/library/logging.handlers.html
  """
  def __init__(self, capacity):
    super(XmlHandler, self).__init__(capacity)
    self._target_file = None
    self._config = None
    self._log_field = "Uninitialized log"
    self._final_fields = {} # node attributes
    self.isClosed = False # precaution as write file done yet
    self.idCommandHandlers = None # have to be set later to know links
    
  def set_target_file(self, filename):
    """
    filename is file name xml with path
    supposedly non existing, no overwrite accepted
    """
    if os.path.exists(filename):
      msg = "XmlHandler target file %s existing yet" % filename
      raise Exception(msg)
    self._target_file = filename

  def set_config(self, config):
    """
    config is supposedly non existing, no overwrite accepted
    """
    if self._config is not None:
      msg = "XmlHandler target config existing yet"
      raise Exception(msg)
    self._config = config
    
  def close(self):
    """
    prepare ElementTree from existing logs and write xml file
    
    warning: avoid sat logging message in logger close phase
    """
    import src.xmlManager as XMLMGR # avoid import cross utilsSat
    targetFile = self._target_file
    config = self._config
    
    # log("dir(XmlHandler)\n" + PP.pformat(dir(self)), True)
    
    if self.isClosed:
      msg = "XmlHandler target file %s closed yet" % targetFile
      log(msg, True) #avoid sat logging message in logger close phase
      return # avoid overwrite

    if os.path.exists(targetFile):
      msg = "XmlHandler target file %s existing yet" % targetFile
      log(msg, True) #avoid sat logging message in logger close phase
      return # avoid overwrite    
    """
    else: # for debug
      msg = "XmlHandler target file %s NOT existing yet" % targetFile
      log(msg, True) #avoid sat logging message in logger close phase
    """
           
    # TODO for debug
    log("XmlHandler to xml file\n%s" % PP.pformat(getListOfStrLogRecord(self.buffer)))
    
    self._log_field = self.createLogField()
       
    xmlFile = XMLMGR.XmlLogFile(targetFile, "SATcommand")
    xmlFile.put_initial_fields(config)    
    xmlFile.put_log_field(self._log_field)
    xmlFile.put_links_fields(self.idCommandHandlers)
    xmlFile.put_final_fields(self._final_fields) 
    xmlFile.write_tree(stylesheet = "command.xsl") # xml complete closed file
    xmlFile.dump_config(config) # create pyconf file in the log directory
    
    self.isClosed = True # precaution to not override xml closed file
    # zaps the buffer to empty as parent class
    super(XmlHandler, self).close() # n.b. extract handler from logger
    
  def createLogFieldFromScrath(self):
    """
    prepare formatted string from self.buffer LogRecord for xml 'Log' node
    local format
    """
    import src.coloringSat as COLS
    res = ""
    for lr in self.buffer:
      fmt = "%s :: %s\n"
      if lr.levelno != LOGI.INFO:
        levelName = COLS.cleanColors(lr.levelname).replace(" ", "")
        msg = COLS.cleanColors(lr.msg)
        res += fmt % (levelName, msg)
    if res == "":
      res = "Empty log"
    return res

  def createLogField(self):
    """
    prepare formatted string from self.buffer LogRecord for xml 'Log' node
    using handler formatter
    """
    import src.coloringSat as COLS
    fmtr = self.formatter
    res = ""
    for lr in self.buffer:
      if lr.levelno != LOGI.INFO: #skip info level and supposed no debug present
        res += fmtr.format(lr) + "\n"
    if res == "":
      res = "Empty log"
    return COLS.cleanColors(res)

    
#################################################################
# methods to define two LoggerSat instances in salomeTools, 
# no more need
#################################################################
def initLoggerAsDefault(logger, fmt=None, level=None):
  """
  init logger as prefixed message and indented message if multi line
  exept info() outed 'as it' without any format.
  level could be modified during execution
  """
  log("initLoggerAsDefault name=%s\nfmt='%s' level='%s'" % (logger.name, fmt, level))
  handler = StreamHandlerSat(sys.stdout) # Logging vers console
  handler.set_name(logger.name + "_console")
  if fmt is not None:
    # formatter = LOGI.Formatter(fmt, "%Y-%m-%d %H:%M:%S")
    formatter = DefaultFormatter(fmt, "%y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
  handler.idCommandHandlers = 0
  logger.addHandler(handler)
  # as RootLogger is level WARNING
  # my logger is not notset but low, handlers needs setlevel greater
  logger.setLevel(LOGI.DEBUG)
  # import src/debug as DBG
  # tmp = (logger.getEffectiveLevel(), LOGI.NOTSET, logger.level, logger.parent.level)
  # DBG.write("logger levels tmp, True)  
  if level is not None: # level could be modified during execution....
    handler.setLevel(level) # on screen log as user wants
  else:
    handler.setLevel(LOGI.INFO) # on screen no log step, which are in xml files
  return
    
  
def initLoggerAsUnittest(logger, fmt=None, level=None):
  """
  init logger as silent on stdout/stderr
  used for retrieve messages in memory for post execution unittest
  https://docs.python.org/2/library/logging.handlers.html
  """
  log("initLoggerAsUnittest name=%s\nfmt='%s' level='%s'" % (logger.name, fmt, level))
  stream = UnittestStream()
  handler = LOGI.StreamHandler(stream) # Logging vers stream
  handler.set_name(logger.name + "_unittest")
  if fmt is not None:
    # formatter = LOGI.Formatter(fmt, "%Y-%m-%d %H:%M:%S")
    formatter = UnittestFormatter(fmt, "%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
  handler.idCommandHandlers = 0
  logger.addHandler(handler)
  logger.stream = stream
  logger.getLogs = stream.getLogs
  logger.getLogsAndClear = stream.getLogsAndClear
  if level is not None:
    logger.setLevel(level)
  else:
    logger.setLevel(LOGI.DEBUG)


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

  
#################################################################
# small tests as demonstration, see unittest also
#################################################################
def testLogger_1(logger):
  """small test"""
  # print getStrDirLogger(logger)
  logger.debug('test logger debug')
  logger.trace('test logger trace')
  logger.info('test logger info')
  logger.warning('test logger warning')
  logger.error('test logger error')
  logger.critical('test logger critical')
  logger.info('\ntest logger info: no indent\n- second line\n- third line\n')
  logger.warning('test logger warning:\n- second line\n- third line')


def testNoReturn(logger):
  """test when message ending '...' and level info then no return mode"""
  logger.warning('BEGIN test NoReturn 1')
  logger.info('test no return here 0...')
  logger.info('have to continue here 1...')
  logger.info('have to continue here 2')
  logger.info('END test NoReturn 1')
  logger.warning('BEGIN test NoReturn 2')
  logger.info('test no return here 0...')
  logger.warning('have NOT to continue here 1...')
  logger.info('have NOT to continue here 2')
  logger.info('END test NoReturn 2')
  


def testMain():
  print("\n**** DEFAULT logger")
  logdef = getDefaultLogger()
  # use of setColorLevelname <color>...<reset>, so do not use %(levelname)-8s
  initLoggerAsDefault(logdef, '%(levelname)s :: %(message)s', level=LOGI.DEBUG)
  testLogger_1(logdef)
  print("\n**** DEFAULT logger NoReturn")
  logdef.testNoReturn()
  
  print("\n**** UNITTEST logger")
  loguni = getUnittestLogger()
  initLoggerAsUnittest(loguni, '%(asctime)s :: %(levelname)-8s :: %(message)s', level=LOGI.DEBUG)
  testLogger_1(loguni) # is silent
  # log("loguni.getLogs():\n%s" % loguni.getLogs())
  print("loguni.streamUnittest:\n%s" % loguni.getLogs())
  print("\n**** UNITTEST logger NoReturn")
  loguni.testNoReturn()
  print("loguni.streamUnittest:\n%s" % loguni.getLogs())
    
  from colorama import Fore as FG
  from colorama import Style as ST
  print("this is unconditionally %scolored in green%s !!!" % (FG.GREEN, ST.RESET_ALL))   



#################################################################
# in production, or not (if __main__)
#################################################################
if __name__ == "__main__":
  # for example, not in production
  # get path to salomeTools sources
  satdir = os.path.dirname(os.path.dirname(__file__))
  # Make the src & commands package accessible from all code
  sys.path.insert(0, satdir)
  testMain() 
  # here we have sys.exit()
else:
  # in production
  # get two LoggerSat instance used in salomeTools, no more needed.
  _loggerDefault = getDefaultLogger()
  _loggerUnittest = getUnittestLogger()
  initLoggerAsDefault(_loggerDefault, '%(levelname)s :: %(message)s')
  initLoggerAsUnittest(_loggerUnittest, '%(asctime)s :: %(levelname)s :: %(message)s')
