#!/usr/bin/env python
#-*- coding:utf-8 -*-

#  Copyright (C) 2010-2012  CEA/DEN
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

import os

import src.debug as DBG
import src.returnCode as RCO
import src.utilsSat as UTS
from src.salomeTools import _BaseCommand
import src.pyconf as PYCONF

########################################################################
# Command class
########################################################################
class Command(_BaseCommand):
  """
  The init command Changes the local settings of SAT
  """
  
  name = "init"
  
  def getParser(self):
    """Define all options for command 'sat init <options>'"""
    parser = self.getParserWithHelp()
    parser.add_option('b', 'base', 'string', 'base', 
                      _('Optional: The path to the products base'))
    parser.add_option('w', 'workdir', 'string', 'workdir', 
                      _('Optional: The path to the working directory '
                        '(where to install the applications'))
    parser.add_option('a', 'archive_dir', 'string', 'archive_dir', 
                      _('Optional: The path to the local archive directory '
                        '(where to install local source archives'))
    parser.add_option('v', 'VCS', 'string', 'VCS', 
                      _('Optional: The address of the repository of SAT '
                        '(only informative)'))
    parser.add_option('t', 'tag', 'string', 'tag', 
                      _('Optional: The tag of SAT (only informative)'))
    parser.add_option('l', 'log_dir', 'string', 'log_dir', 
                      _('Optional: The directory where to put all the logs of SAT'))
    return parser

  def run(self, cmd_arguments):
    """method called for command 'sat init <options>'"""
    argList = self.assumeAsList(cmd_arguments)

    # print general help and returns
    if len(argList) == 0:
      self.print_help()
      return RCO.ReturnCode("OK", "No arguments, as 'sat %s --help'" % self.name)
      
    self._options, remaindersArgs = self.parseArguments(argList)
    
    if self._options.help:
      self.print_help()
      return RCO.ReturnCode("OK", "Done 'sat %s --help'" % self.name)
   
    # shortcuts
    runner = self.getRunner()
    config = self.getConfig()
    logger = self.getLogger()
    options = self.getOptions()
   
    # Print some informations
    logger.info(_('Local Settings of SAT %s') % UTS.label(config.VARS.salometoolsway))

    res = []
    # Set the options corresponding to a directory
    for opt in [("base" , options.base),
                ("workdir", options.workdir),
                ("log_dir", options.log_dir),
                ("archive_dir", options.archive_dir)]:
      key, value = opt
      if value:
        rc = check_path(value, logger)
        res.append(rc)
        if rc.isOk():
          rc = set_local_value(config, key, value, logger)
          res.append(rc)

    # Set the options corresponding to an informative value            
    for opt in [("VCS", options.VCS), ("tag", options.tag)]:
      key, value = opt
      rc = set_local_value(config, key, value, logger)
      res.append(rc)
    
    msg = get_str_local_values(config)
    logger.info(msg)
    
    res = RCO.ReturnCodeFromList(res)
    return res


def set_local_value(config, key, value, logger):
    """Edit the site.pyconf file and change a value.

    :param config: (Config) The global configuration.    
    :param key: (str) The key from which to change the value.
    :param value: (str) The path to change.
    :param logger: (Logger) The logger instance.
    :return: (RCO.ReturnCode)
    """
    local_file_path = os.path.join(config.VARS.datadir, "local.pyconf")
    # Update the local.pyconf file
    try:
      local_cfg = PYCONF.Config(local_file_path)
      local_cfg.LOCAL[key] = value
      with open(local_file_path, 'w') as ff:
        local_cfg.__save__(ff, 1)     
      if key != "log_dir":
        config.LOCAL[key] = value
    except Exception as e:
      err = str(e)
      msg = "Unable to update the local.pyconf file: %s" % str(e)
      logger.error(msg)
      return RCO.ReturnCode("KO", msg)
    
    return RCO.ReturnCode("OK")
    
def get_str_local_values(config):
    """get string to display the base path

    :param config: (Config) The global configuration.
    :return: (str) with infos from config
    """
    loc = config.LOCAL
    info = [("base", loc.base),
            ("workdir", loc.workdir),
            ("log_dir", loc.log_dir),
            ("archive_dir", loc.archive_dir),
            ("VCS", loc.VCS),
            ("tag", loc.tag)]
    res = UTS.formatTuples(info)
    return res

def check_path(path_to_check, logger):
    """Verify that the given path is not a file and can be created.
    
    :param path_to_check: (str) The path to check.
    :param logger: (Logger) The logger instance.
    """
    if path_to_check == "default":
      return RCO.ReturnCode("OK", "check_path default")
    
    
    # If it is a file, do nothing and return error
    if os.path.isfile(path_to_check):
      msg = _("""\
The given path is a file: %s
Please provide a path to a directory""") % UTS.blue(path_to_check)
      logger.error(msg)
      return RCO.ReturnCode("KO", "%s have to be directory, is file" % path_to_check)
      
    # Try to create the given path
    try:
      UTS.ensure_path_exists(path_to_check)
    except Exception as e:
      msg = "Unable to create the directory %s:\n%s" % (UTS.blue(path_to_check), UTS.yellow(str(e)))
      logger.error(msg)
      return RCO.ReturnCode("KO", "Unable to create the directory %s" % path_to_check)
    
    return RCO.ReturnCode("OK", "check_path %s" % path_to_check)
