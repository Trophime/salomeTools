#!/usr/bin/env python
#-*- coding:utf-8 -*-
#  Copyright (C) 2010-2013  CEA/DEN
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

import src


def description():
    '''method that is called when salomeTools is called with --help option.
    
    :return: The text to display for the run command description.
    :rtype: str
    '''
    return _("This command runs the application launcher"
             " with the given arguments.\n\nexample:\nsat run SALOME-master")

def run(args, runner, logger):
    '''method that is called when salomeTools is called with run parameter.
    '''

    # check for product
    src.check_config_has_application(runner.cfg)

    # Determine launcher path 
    launcher_name = src.get_launcher_name(runner.cfg)
    launcher_dir = runner.cfg.APPLICATION.workdir
    
    # Check the launcher existence
    if launcher_name not in  os.listdir(launcher_dir):
        message = _("""\
The launcher %(1)s was not found in directory '%(2)s'.
Did you run the command 'sat launcher' ?\n""" % {"1": launcher_name, "2": launcher_dir} )
        raise src.SatException(message)
          
    launcher_path = os.path.join(launcher_dir, launcher_name)

    if not os.path.exists(launcher_path):
        message = _("""\
The launcher at path '%s' is missing.
Did you run the command 'sat launcher' ?\n""" % launcher_path )
        raise src.SatException(message)

    # Determine the command to launch (add the additional arguments)
    command = launcher_path + " " + " ".join(args)

    # Print the command
    src.printcolors.print_value(logger, _("Executed command"), command, 2)
    logger.write(_("Launching ...\n"))
    logger.flush()
    
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
