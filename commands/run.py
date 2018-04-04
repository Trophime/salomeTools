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
import subprocess

import src.debug as DBG
import src.returnCode as RCO
import src.utilsSat as UTS
from src.salomeTools import _BaseCommand

########################################################################
# Command class
########################################################################
class Command(_BaseCommand):
  """\
  The run command runs the application launcher with the given arguments.
  
  examples:
    >> sat run SALOME
  """
  
  name = "run"
  
  def getParser(self):
    """Define all options for command 'sat run <options>'"""
    parser = self.getParserWithHelp() # no options yet
    return parser

  def run(self, cmd_arguments):
    """method called for command 'sat run <options>'"""
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

    # check for product
    src.check_config_has_application(runner.cfg)

    # Determine launcher path 
    launcher_name = src.get_launcher_name(runner.cfg)
    launcher_dir = runner.cfg.APPLICATION.workdir
    
    # Check the launcher existence
    if launcher_name not in  os.listdir(launcher_dir):
        message = _("""\
The launcher %(1)s was not found in directory '%(2)s'.
Did you run the command 'sat launcher' ?\n""") % {"1": launcher_name, "2": launcher_dir}
        raise Exception(message)
          
    launcher_path = os.path.join(launcher_dir, launcher_name)

    if not os.path.exists(launcher_path):
        message = _("""\
The launcher at path '%s' is missing.
Did you run the command 'sat launcher' ?\n""") % launcher_path
        raise Exception(message)

    # Determine the command to launch (add the additional arguments)
    command = launcher_path + " " + " ".join(args)

    # Print the command
    logger.info(_("Executed command <blue>%s<reset> Launching ...\n") % command)
    
    # Run the launcher
    subprocess.call(command,
                    shell=True,
                    stdout=logger.logTxtFile,
                    stderr=subprocess.STDOUT)
    
    # Display information : how to get the logs
    messageFirstPart = _("\nEnd of execution. To see the traces, "
                         "please tap the following command :\n")
    messageSecondPart = src.printcolors.printcLabel(
                                            runner.cfg.VARS.salometoolsway +
                                            os.sep +
                                            "sat log " +
                                            runner.cfg.VARS.application + "\n")
    logger.write("  %s\n" %(messageFirstPart + messageSecondPart), 2)
    
    return 0
