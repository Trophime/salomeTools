#!/usr/bin/env python
#-*- coding:utf-8 -*-

#  Copyright (C) 2010-2018  CEA/DEN
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 2.1 of the License.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA

"""
utilities for sat
general useful simple methods
all-in-one import srs.utilsSat as UTS

| Usage:
| >> import srsc.utilsSat as UTS
| >> UTS.ensure_path_exists(path)
"""

import os
import shutil
import errno
import stat

import re
import tempfile
import subprocess as SP

import src.returnCode as RCO
import src.debug as DBG # Easy print stderr (for DEBUG only)


##############################################################################
# file system utilities
##############################################################################
def get_CONFIG_FILENAME():
    """get initial config.pyconf"""
    return "sat-config.pyconf"
    
def ensure_path_exists(path):
    """Create a path if not existing
    
    :param path: (str) The path.
    """
    # DBG.write("ensure_path_exists", path, True)
    if not os.path.exists(path):
        os.makedirs(path)
        
def ensure_file_exists(aFile, aDefaultFile):
    """
    Create a file if not existing,
    copying from default file
    
    :param aFilepath: (str) The file to ensure existence
    :param aDefaultFile: (str) The default file to copy if not existing
    """
    isfile = os.path.isfile(aFile)
    if isfile: return True
    try:
      DBG.write("ensure_file_exists %s" % isfile, aDefaultFile + " -->\n" + aFile)
      shutil.copy2(aDefaultFile, aFile)
      return True
    except:
      return False

        
def replace_in_file(file_in, str_in, str_out):
    """
    Replace <str_in> by <str_out> in file <file_in>.
    save a file old version as file_in + '_old'

    :param file_in: (str) The file name
    :param str_in: (str) The string to search
    :param str_out: (str) The string to replace.    
    """
    with open(file_in, "r") as f: 
      contents = f.read()
    shutil.move(file_in, file_in + "_old")
    with open(file_in, "w") as f: 
      f.write(contents.replace(str_in, str_out))
  
##############################################################################
# Utils class to simplify path manipulations.
##############################################################################
class Path:
    def __init__(self, path):
        self.path = str(path)

    def __add__(self, other):
        return Path(os.path.join(self.path, str(other)))

    def __abs__(self):
        return Path(os.path.abspath(self.path))

    def __str__(self):
        return self.path

    def __eq__(self, other):
        return self.path == other.path

    def exists(self):
        return self.islink() or os.path.exists(self.path)

    def islink(self):
        return os.path.islink(self.path)

    def isdir(self):
        return os.path.isdir(self.path)

    def isfile(self):
        return os.path.isfile(self.path)

    def list(self):
        return [Path(p) for p in os.listdir(self.path)]

    def dir(self):
        return Path(os.path.dirname(self.path))

    def base(self):
        return Path(os.path.basename(self.path))

    def make(self, mode=None):
        os.makedirs(self.path)        
        if mode:
            os.chmod(self.path, mode)
        
    def chmod(self, mode):
        os.chmod(self.path, mode)

    def rm(self):    
        if self.islink():
            os.remove(self.path)
        else:
            shutil.rmtree( self.path, onerror = handleRemoveReadonly )

    def copy(self, path, smart=False):
        if not isinstance(path, Path):
            path = Path(path)

        if os.path.islink(self.path):
            return self.copylink(path)
        elif os.path.isdir(self.path):
            return self.copydir(path, smart)
        else:
            return self.copyfile(path)

    def smartcopy(self, path):
        return self.copy(path, True)

    def readlink(self):
        if self.islink():
            return os.readlink(self.path)
        else:
            return False

    def symlink(self, path):
        try:
            os.symlink(str(path), self.path)
            return True
        except:
            return False

    def copylink(self, path):
        try:
            os.symlink(os.readlink(self.path), str(path))
            return True
        except:
            return False

    def copydir(self, dst, smart=False):
        try:
            names = self.list()

            if not dst.exists():
                dst.make()

            for name in names:
                if name == dst:
                    continue
                if smart and (str(name) in [".git", "CVS", ".svn"]):
                    continue
                srcname = self + name
                dstname = dst + name
                srcname.copy(dstname, smart)
            return True
        except:
            return False

    def copyfile(self, path):
        try:
            shutil.copy2(self.path, str(path))
            return True
        except:
            return False

def find_file_in_lpath(file_name, lpath, additional_dir = ""):
    """
    Find the file that has the same name as file_name ,
    searching in directories listed in lpath. 
    If it is found, return the full path of the file, else, return False. 
    The additional_dir (optional) is the name of the directory 
    to add to all paths in lpath.
    
    :param file_name: (str) The file name to search
    :param lpath: (list) The list of directories where to search
    :param additional_dir: (str) The name of the additional directory
    :return: (ReturnCode) The full path of the file or False if not found
    """
    if len(lpath) < 1:
      raise Exception("find file with no directories to search into")
    for directory in lpath:
      dir_complete = os.path.join(directory, additional_dir)
      if not os.path.isdir(directory) or not os.path.isdir(dir_complete):
        continue
      l_files = os.listdir(dir_complete)
      for file_n in l_files:
        if file_n == file_name:
          found = os.path.join(dir_complete, file_name)
          return RCO.ReturnCode("OK", "file %s found" % file_name, found)
     
    return RCO.ReturnCode("KO", "file %s not found" % file_name)

def handleRemoveReadonly(func, path, exc):
    excvalue = exc[1]
    if func in (os.rmdir, os.remove) and excvalue.errno == errno.EACCES:
        os.chmod(path, stat.S_IRWXU| stat.S_IRWXG| stat.S_IRWXO) # 0777
        func(path)
    else:
        raise
        
##############################################################################
# pyconf config utilities
##############################################################################
        
def check_has_key(inConfig, key):
    """Check that the in-Config node has the named key (as an attribute) 
    
    :param inConfig: (Config or Mapping etc) The in-Config node
    :param key: (str) The key to check presence in in-Config node
    :return: (RCO.ReturnCode) 'OK' if presence
    """
    debug = True
    if key not in inConfig:
      msg = _("check_has_key '%s' not found" % key)
      DBG.write("check_has_key", msg, debug)
      return RCO.ReturnCode("KO", msg)
    else:
      msg = _("check_has_key '%s' found" % key)
      DBG.write("check_has_key", msg, debug)
      return RCO.ReturnCode("OK", msg)
         
def check_config_has_application(config):
    """
    Check that the config has the key APPLICATION. 
    Else raise an exception.
    
    :param config: (Config) The config.
    """
    if 'APPLICATION' not in config:
      msg = _("An application name is required.")
      msg += "\n" + _("(as 'sat prepare <application>')")
      msg += "\n" + _("Use 'sat config --list' to get the list of available applications.")
      DBG.write("check_config_has_application", msg)
      return RCO.ReturnCode("KO", msg)
    else:
      msg = _("APPLICATION '%s' found." % config)
      DBG.write("check_config_has_application", msg)
      return RCO.ReturnCode("OK", msg)

def check_config_has_profile(config):
    """
    Check that the config has the key APPLICATION.profile.
    Else, raise an exception.
    
    :param config: (Config) The config.
    """
    check_config_has_application(config).raiseIfKo()
    if 'profile' not in config.APPLICATION:
      msg = _("An 'APPLICATION.profile' section is required in config.")
      return RCO.ReturnCode("KO", msg)
    else:
      msg = _("An 'APPLICATION.profile' is found in config.")
      return RCO.ReturnCode("OK", msg)

def get_config_key(inConfig, key, default):
    """
    Search for key value in config node 'inConfig[key]' as 'inConfig.key'
    If key is not in inCconfig, then return default,
    else, return the found value
       
    :param inConfig: (Config or Mapping etc) The in-Config node.
    :param key: (str) the name of the parameter to get the value
    :param default: (str) The value to return if key is not in-Config
    :return: (if supposedly leaf (str),else (in-Config Node) 
    """
    if check_has_key(inConfig, key).isOk():
      return inConfig[key]
    else:
      return default

def get_base_path(config):
    """Returns the path of the products base.
    
    :param config: (Config) The global Config instance.
    :return: (str) The path of the products base.
    """
    if "base" not in config.LOCAL:
        local_file_path = os.path.join(config.VARS.salometoolsway, "data", "local.pyconf")
        msg = _("Please define a base path in the file %s") % local_file_path
        raise Exception(msg)
        
    base_path = os.path.abspath(config.LOCAL.base)   
    return base_path

def get_launcher_name(config):
    """Returns the name of application file launcher, 'salome' by default.
    
    :param config: (Config) The global Config instance.
    :return: (str) The name of salome launcher.
    """
    check_config_has_application(config).raiseIfKo()
    if 'profile' in config.APPLICATION and \
       'launcher_name' in config.APPLICATION.profile:
        launcher_name = config.APPLICATION.profile.launcher_name
    else:
        launcher_name = 'salome'
    return launcher_name


def get_log_path(config):
    """Returns the path of the logs.
    
    :param config: (Config) The global Config instance.
    :return: (str) The path of the logs.
    """
    if "log_dir" not in config.LOCAL:
        local_file_path = os.path.join(
          config.VARS.salometoolsway, "data", "local.pyconf" )
        msg = _("Please define a log_dir in the file %s") % local_file_path
        raise Exception(msg)
      
    log_dir_path = os.path.abspath(config.LOCAL.log_dir)
    return log_dir_path

def get_salome_version(config):
  
    import src.product as PROD # avoid cross import
    
    if hasattr(config.APPLICATION, 'version_salome'):
        Version = config.APPLICATION.version_salome
    else:
        KERNEL_info = PROD.get_product_config(config, "KERNEL")
        VERSION = os.path.join(
          KERNEL_info.install_dir, "bin", "salome", "VERSION" )
        if not os.path.isfile(VERSION):
            return None
            
        fVERSION = open(VERSION)
        Version = fVERSION.readline()
        fVERSION.close()
        
    VersionSalome = int(only_numbers(Version))    
    return VersionSalome

def only_numbers(str_num):
    return ''.join([nb for nb in str_num if nb in '0123456789'] or '0')

def read_config_from_a_file(filePath):
    try:
        cfg_file = pyconf.Config(filePath)
    except pyconf.ConfigError as e:
        raise Exception(_("Error in configuration file: %(file)s\n  %(error)s") %
            { 'file': filePath, 'error': str(e) } )
    return cfg_file

def get_tmp_filename(config, name):
    if not os.path.exists(config.VARS.tmp_root):
        os.makedirs(config.VARS.tmp_root)

    return os.path.join(config.VARS.tmp_root, name)

def get_property_in_product_cfg(product_cfg, pprty):
    if not "properties" in product_cfg:
        return None
    if not pprty in product_cfg.properties:
        return None
    return product_cfg.properties[pprty]

##############################################################################
# logger utilities
##############################################################################
def formatTuples(tuples):
    """
    Format 'label = value' the tuples in a tabulated way.
    
    :param tuples: (list) The list of tuples to format
    :return: (str) The tabulated text. (as mutiples lines)
    """
    # find the maximum length of the first value of the tuples
    smax = max(map(lambda l: len(l[0]), tuples))
    # Print each item of tuples with good indentation
    msg = ""
    for i in tuples:
        sp = " " * (smax - len(i[0]))
        msg += sp + "%s = %s\n" % (i[0], i[1]) # tuples, may be longer
    if len(tuples) > 1: msg += "\n" # for long list
    return msg
    
def formatValue(label, value, suffix=""):
    """
    format 'label = value' with the info color
    
    :param label: (int) the label to print.
    :param value: (str) the value to print.
    :param suffix: (str) the optionnal suffix to add at the end.
    """
    msg = "  %s = %s %s" % (label, value, suffix)
    return msg
    
def logger_info_tuples(logger, tuples):
    """
    For convenience
    format as formatTuples() and call logger.info()
    """
    msg = formatTuples(tuples)
    logger.info(msg)

def log_step(logger, header, step):
    logger.info("\r%s%s" % (header, " " * 20))
    logger.info("\r%s%s" % (header, step))

def log_res_step(logger, res):
    if res == 0:
        logger.info("<OK>\n")
    else:
        logger.info("<KO>\n")

##############################################################################
# color utilities, for convenience    
##############################################################################
_colors = "BLACK RED GREEN YELLOW BLUE MAGENTA CYAN WHITE".lower().split(" ")
    
def black(msg):
    return "<black>"+msg+"<reset>"

def red(msg):
    return "<red>"+msg+"<reset>"

def green(msg):
    return "<green>"+msg+"<reset>"

def yellow(msg):
    return "<yellow>"+msg+"<reset>"

def blue(msg):
    return "<blue>"+msg+"<reset>"

def magenta(msg):
    return "<magenta>"+msg+"<reset>"

def cyan(msg):
    return "<cyan>"+msg+"<reset>"

def white(msg):
    return "<white>"+msg+"<reset>"

def normal(msg):
    return "<normal>"+msg+"<reset>"

def reset(msg):
    return "<reset>"+msg

def info(msg):
    return "<info>"+msg+"<reset>"

def header(msg):
    return "<info>"+msg+"<reset>"

def label(msg):
    return "<label>"+msg+"<reset>"

def success(msg):
    return "<success>"+msg+"<reset>"

def warning(msg):
    return "<warning>"+msg+"<reset>"

def error(msg):
    return "<error>"+msg+"<reset>"

def critical(msg):
    return "<critical>"+msg+"<reset>"


##############################################################################
# list and dict utilities
##############################################################################
def deepcopy_list(input_list):
    """Do a deep copy of a list
    
    :param input_list: (list) The list to copy
    :return: (list) The copy of the list
    """
    res = []
    for elem in input_list:
        res.append(elem)
    return res

def remove_item_from_list(input_list, item):
    """Remove all occurences of item from input_list
    
    :param input_list: (list) The list to modify
    :return: (list) The without any item
    """
    res = []
    for elem in input_list:
        if elem == item:
            continue
        res.append(elem)
    return res

def merge_dicts(*dict_args):
    """
    Given any number of dicts, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dicts.
    """
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result
    
    
##############################################################################
# log utilities (TODO: set in loggingSat class, later, changing tricky xml?
##############################################################################    
        
_log_macro_command_file_expression = "^[0-9]{8}_+[0-9]{6}_+.*\.xml$"
_log_all_command_file_expression = "^.*[0-9]{8}_+[0-9]{6}_+.*\.xml$"

def show_command_log(logFilePath, cmd, application, notShownCommands):
    """
    Used in updateHatXml. 
    Determine if the log xml file logFilePath 
    has to be shown or not in the hat log.
    
    :param logFilePath: (str) the path to the command xml log file
    :param cmd: (str) the command of the log file
    :param application: (str) 
      The application passed as parameter to the salomeTools command
    :param notShownCommands: (list) 
      The list of commands that are not shown by default
    :return: (RCO.ReturnCode)
      OK if cmd is not in notShownCommands and the application 
      in the log file corresponds to application
      ReturnCode value is tuple (appliLog, launched_cmd)
    """
    # When the command is not in notShownCommands, no need to go further :
    # Do not show
    
    import src.xmlManager as XMLMGR # avoid import cross utilsSat
    
    if cmd in notShownCommands:
        return RCO.ReturnCode("KO", "command '%s' in notShownCommands" % cmd, None)
 
    # Get the application of the log file
    try:
        logFileXml = XMLMGR.ReadXmlFile(logFilePath)
    except Exception as e:
        msg = _("The log file '%s' cannot be read" % logFilePath)
        return RCO.ReturnCode("KO", msg, None)

    if 'application' in logFileXml.xmlroot.keys():
        appliLog = logFileXml.xmlroot.get('application')
        launched_cmd = logFileXml.xmlroot.find('Site').attrib['launchedCommand']
        # if it corresponds, then the log has to be shown
        if appliLog == application:
            return RCO.ReturnCode("OK", "appliLog is application", (appliLog, launched_cmd))
        elif application != 'None':
            return RCO.ReturnCode("KO", "application is not 'None'", (appliLog, launched_cmd))
        
        return RCO.ReturnCode("OK", "", (appliLog, launched_cmd))
    
    if application == 'None':
        return RCO.ReturnCode("OK", "application == 'None'", (None, None))
        
    return RCO.ReturnCode("KO", "", (None, None))

def list_log_file(dirPath, expression):
    """Find all files corresponding to expression in dirPath
    
    :param dirPath: (str) the directory where to search the files
    :param expression: (str) the regular expression of files to find
    :return: (list) the list of files path and informations about it
    """
    lRes = []
    for fileName in os.listdir(dirPath):
        # YYYYMMDD_HHMMSS_namecmd.xml
        sExpr = expression
        oExpr = re.compile(sExpr)
        if oExpr.search(fileName):
            file_name = fileName
            if fileName.startswith("micro_"):
                file_name = fileName[len("micro_"):]
            # get date and hour and format it
            date_hour_cmd_host = file_name.split('_')
            date_not_formated = date_hour_cmd_host[0]
            date = "%s/%s/%s" % (date_not_formated[6:8], 
                                 date_not_formated[4:6], 
                                 date_not_formated[0:4])
            hour_not_formated = date_hour_cmd_host[1]
            hour = "%s:%s:%s" % (hour_not_formated[0:2], 
                                 hour_not_formated[2:4], 
                                 hour_not_formated[4:6])
            if len(date_hour_cmd_host) < 4:
                cmd = date_hour_cmd_host[2][:-len('.xml')]
                host = ""
            else:
                cmd = date_hour_cmd_host[2]
                host = date_hour_cmd_host[3][:-len('.xml')]
            lRes.append((os.path.join(dirPath, fileName), 
                         date_not_formated,
                         date,
                         hour_not_formated,
                         hour,
                         cmd,
                         host))
    return lRes

def update_hat_xml(logDir, application=None, notShownCommands = []):
    """
    Create the xml file in logDir that contain all the xml file 
    and have a name like YYYYMMDD_HHMMSS_namecmd.xml
    
    :param logDir: (str) the directory to parse
    :param application: (str) the name of the application if there is any
    """
    # Create an instance of XmlLogFile class to create hat.xml file
    
    import src.xmlManager as XMLMGR # avoid import cross utilsSat 
    
    xmlHatFilePath = os.path.join(logDir, 'hat.xml')
    xmlHat = XMLMGR.XmlLogFile(xmlHatFilePath, "LOGlist", {"application" : application})
    # parse the log directory to find all the command logs, 
    # then add it to the xml file
    lLogFile = list_log_file(logDir, _log_macro_command_file_expression)
    for filePath, __, date, __, hour, cmd, __ in lLogFile:
        showLog, cmdAppli, full_cmd = show_command_log(filePath, cmd,
                                              application, notShownCommands)
        #if cmd not in notShownCommands:
        if showLog:
            # add a node to the hat.xml file
            atts = {"date" : date, "hour" : hour, "cmd" : cmd, "application" : cmdAppli, "full_command" : full_cmd}
            txt = os.path.basename(filePath)
            xmlHat.add_simple_node_root("LogCommand", text=txt, attrib=atts)
    
    # Write the file on the hard drive
    xmlHat.write_tree('hat.xsl')
    

##############################################################################
# subprocess utilities, with logger functionnalities (trace etc.)
##############################################################################
    
def Popen(command, shell=True, cwd=None, env=None, stdout=SP.PIPE, stderr=SP.PIPE, logger=None):
  """
  make subprocess.Popen(cmd), with 
  call logger.trace and logger.error if problem as returncode != 0 
  """
  if True: #try:  
    proc = SP.Popen(command, shell=shell, cwd=cwd, env=env, stdout=stdout, stderr=SP.STDOUT)
    res_out, res_err = proc.communicate() # res_err = None as stderr=SP.STDOUT
    rc = proc.returncode
    
    DBG.write("Popen logger returncode", (rc, res_out))
    
    if rc == 0:
      if logger is not None:
        logger.trace("<OK> launch command rc=%s cwd=<info>%s<reset>:\n%s" % (rc, cwd, command))
        logger.trace("<OK> result command stdout&stderr:\n%s" % res_out)
      return RCO.ReturnCode("OK", "command done", value=res_out)
    else:
      if logger is not None:
        logger.warning("<KO> launch command rc=%s cwd=<info>%s<reset>:\n%s" % (rc, cwd, command))
        logger.warning("<KO> result command stdout&stderr:\n%s" % res_out)
      return RCO.ReturnCode("KO", "command problem", value=res_out)
  else: #except Exception as e:
    logger.error("<KO> launch command cwd=%s:\n%s" % (cwd, command))
    logger.error("launch command exception:\n%s" % e)
    return RCO.ReturnCode("KO", "launch command problem")

  
def generate_catalog(machines, config, logger):
    """Generates the catalog from a list of machines."""
    # remove empty machines
    machines = map(lambda l: l.strip(), machines)
    machines = filter(lambda l: len(l) > 0, machines)

    logger.debug("  %s = %s" % _("Generate Resources Catalog"), ", ".join(machines))
    
    cmd = '"cat /proc/cpuinfo | grep MHz ; cat /proc/meminfo | grep MemTotal"'
    user = getpass.getuser()

    msg = ""
    machine = """\
  <machine
    protocol="ssh"
    nbOfNodes="1"
    mode="interactif"
    OS="LINUX"
    CPUFreqMHz="%s"
    nbOfProcPerNode="%s"
    memInMB="%s"
    userName="%s"
    name="%s"
    hostname="%s"/>
"""
    for k in machines:
      logger.info("    ssh %s " % (k + " ").ljust(20, '.'), 4)

      ssh_cmd = 'ssh -o "StrictHostKeyChecking no" %s %s' % (k, cmd)
      res = UTS.Popen(ssh_cmd, shell=True)
      if res.isOk():
        lines = p.stdout.readlines()
        freq = lines[0][:-1].split(':')[-1].split('.')[0].strip()
        nb_proc = len(lines) -1
        memory = lines[-1].split(':')[-1].split()[0].strip()
        memory = int(memory) / 1000
        msg += machine % (freq, nb_proc, memory, user, k, k)
            
    catfile = UTS.get_tmp_filename(config, "CatalogResources.xml")
    with open(catfile, "w") as f:
      f.write("""\
<!DOCTYPE ResourcesCatalog>
<resources>
%s
</resources>
""" % msg)
    return catfile

