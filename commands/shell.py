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


import subprocess

import src.debug as DBG
import src.returnCode as RCO
from src.salomeTools import _BaseCommand

########################################################################
# Command class
########################################################################
class Command(_BaseCommand):
  """\
  The shell command executes the shell command passed as argument.

  examples:
    >> sat shell --command 'ls -lt /tmp'
  """
  
  name = "shell"
  
  def getParser(self):
    """Define all options for the command 'sat shell <options>'"""
    parser = self.getParserWithHelp()
    parser.add_option('c', 'command', 'string', 'command',
                      _('Mandatory: The shell command to execute.'), "")
    return parser

  def run(self, cmd_arguments):
    """method called for command 'sat shell <options>'"""
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
  
    # Make sure the command option has been called
    if not options.command:
        msg = _("The option --command is required\n")      
        logger.error(msg)
        return 1
    
    # Print the input command
    msg = _("Command to execute:\n%s\nExecution ... ") % options.command
    logger.info(msg)
    
    # Call the input command
    res = subprocess.call(options.command,
                          shell=True,
                          stdout=logger.logTxtFile,
                          stderr=subprocess.STDOUT)
   
    # Format the result to be 0 (success) or 1 (fail)
    if res != 0:
        status = "KO"
    else:
        status = "OK"
        
    logger.info("<%s>\n" % status)
    return RCO.ReturnCode(status, "shell command done")
