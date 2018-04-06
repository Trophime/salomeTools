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


import src.debug as DBG
import src.returnCode as RCO
from src.salomeTools import _BaseCommand
import src.pyconf as PYCONF

########################################################################
# Command class
########################################################################
class Command(_BaseCommand):
  """\
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
    logger.write(_('Local Settings of SAT %s\n\n') % \
                UTS.label(runner.cfg.VARS.salometoolsway), 1)

    res = 0
    
    # Set the options corresponding to a directory
    for opt in [("base" , options.base),
                ("workdir", options.workdir),
                ("log_dir", options.log_dir),
                ("archive_dir", options.archive_dir)]:
        key, value = opt
        if value:
            res_check = check_path(value, logger)
            res += res_check
            if res_check == 0:
                res_set = set_local_value(runner.cfg, key, value, logger)
                res += res_set

    # Set the options corresponding to an informative value            
    for opt in [("VCS", options.VCS), ("tag", options.tag)]:
        key, value = opt
        res_set = set_local_value(runner.cfg, key, value, logger)
        res += res_set
    
    display_local_values(runner.cfg, logger)
    
    return res


def set_local_value(config, key, value, logger):
    """ Edit the site.pyconf file and change a value.

    :param config Config: The global configuration.    
    :param key Str: The key from which to change the value.
    :param value Str: The path to change.
    :param logger Logger: The logger instance.
    :return: 0 if all is OK, else 1
    :rtype: int
    """
    local_file_path = os.path.join(config.VARS.datadir, "local.pyconf")
    # Update the local.pyconf file
    try:
        local_cfg = PYCONF.Config(local_file_path)
        local_cfg.LOCAL[key] = value
        ff = open(local_file_path, 'w')
        local_cfg.__save__(ff, 1)
        ff.close()
        if key != "log_dir":
            config.LOCAL[key] = value
    except Exception as e:
        err = str(e)
        msg = _("Unable to update the local.pyconf file: %s\n") % err
        logger.write(msg, 1)
        return 1
    
    return 0
    
def display_local_values(config, logger):
    """ Display the base path

    :param config Config: The global configuration.
    :param key Str: The key from which to change the value.
    :param logger Logger: The logger instance.
    """
    info = [("base", config.LOCAL.base),
            ("workdir", config.LOCAL.workdir),
            ("log_dir", config.LOCAL.log_dir),
            ("archive_dir", config.LOCAL.archive_dir),
            ("VCS", config.LOCAL.VCS),
            ("tag", config.LOCAL.tag)]
    UTS.logger_info_tuples(logger, info)

    return 0

def check_path(path_to_check, logger):
    """ Verify that the given path is not a file and can be created.
    
    :param path_to_check Str: The path to check.
    :param logger Logger: The logger instance.
    """
    if path_to_check == "default":
        return 0
    
    # Get the path
    path = src.Path(path_to_check)
    
    # If it is a file, do nothing and return error
    if path.isfile():
        msg = _("""\
The given path is a file: %s
Please provide a path to a directory\n""") % UTS.blue(path_to_check)
        logger.error(msg)
        return 1
      
    # Try to create the given path
    try:
        src.ensure_path_exists(str(path))
    except Exception as e:
        msg = _("""\
Unable to create the directory %s:

%s\n""") % (UTS.blue(str(path)), UTS.yellow(e)
        logger.error(msg)
        return 1
    
    return 0
