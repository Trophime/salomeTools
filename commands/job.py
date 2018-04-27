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

########################################################################
# Command class
########################################################################
class Command(_BaseCommand):
  """\
  The job command executes the commands of the job defined
  in the jobs configuration file\
  
  examples:
    >> sat job --jobs_config my_jobs --name my_job"
  """
  
  name = "job"
  
  def getParser(self):
    """Define all options for command 'sat job <options>'"""
    parser = self.getParserWithHelp()
    parser.add_option(
        'j', 'jobs_config', 'string', 'jobs_cfg', 
        _('Mandatory: The name of the config file that contains the jobs configuration') )
    parser.add_option(
        '', 'name', 'string', 'job',
        _('Mandatory: The job name from which to execute commands.'), "" )
    return parser

  def run(self, cmd_arguments):
    """method called for command 'sat job <options>'"""
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
         
    l_cfg_dir = config.PATHS.JOBPATH
    
    # Make sure the jobs_config option has been called
    if not options.jobs_cfg:
        message = _("The option --jobs_config is required\n")      
        logger.error(message)
        return 1
    
    # Make sure the name option has been called
    if not options.job:
        message = _("The option --name is required\n")      
        logger.error(message)
        return 1
    
    # Find the file in the directories
    found = True
    fPyconf = options.jobs_cfg
    if not file_jobs_cfg.endswith('.pyconf'): 
        fPyconf += '.pyconf'
        
    for cfg_dir in l_cfg_dir:
        file_jobs_cfg = os.path.join(cfg_dir, fPyconf)
        if os.path.exists(file_jobs_cfg):
            found = True
            break

    if not found:
        msg = _("""\
The job file configuration %s was not found.
Use the --list option to get the possible files.""") % UTS.blue(fPyconf)
        logger.error(msg)
        return 1
    
    info = [ (_("Platform"), config.VARS.dist),
             (_("File containing the jobs configuration"), file_jobs_cfg) ]
    UTS.logger_info_tuples(logger, info)
    
    # Read the config that is in the file
    config_jobs = src.read_config_from_a_file(file_jobs_cfg)
    
    # Find the job and its commands
    found = False
    for job in config_jobs.jobs:
        if job.name == options.job:
            commands = job.commands
            found = True
            break
    if not found:
        msg = _("Impossible to find the job %s in %s\n") % (options.job, file_jobs_cfg)
        logger.error(msg)
        return 1
    
    # Find the maximum length of the commands in order to format the display
    len_max_command = max([len(cmd) for cmd in commands])
    
    # Loop over the commands and execute it
    res = 0
    nb_pass = 0
    for command in commands:
        specific_option = False
        # Determine if it is a sat command or a shell command
        cmd_exe = command.split(" ")[0] # first part
        if cmd_exe == "sat":
            # use the salomeTools parser to get the options of the command
            sat_parser = salomeTools.parser
            input_parser = src.remove_item_from_list(command.split(' ')[1:], "")
            (options, argus) = sat_parser.parse_args(input_parser)
            # Verify if there is a changed option
            for attr in dir(options):
                if attr.startswith("__"):
                    continue
                if options.__getattr__(attr) != None:
                    specific_option = True
            sat_command_name = argus[0]
            end_cmd = " ".join(argus[1:])
        else:
            sat_command_name = "shell"
            end_cmd = ["--command", command]
        # Do not change the options if no option was called in the command
        if not(specific_option):
            options = None

        # Get dynamically the command function to call
        sat_command = runner.__getattr__(sat_command_name)

        logger.info("Executing " + UTS.label(command) + " " +
                    "." * (len_max_command - len(command)) + " ")
        
        error = ""
        # Execute the command
        code = sat_command(end_cmd,
                           options = options,
                           batch = True,
                           verbose = 0,
                           logger_add_link = logger)
            
        # Print the status of the command
        if code == 0:
            nb_pass += 1
            logger.info("<OK>\n")
        else:
            if sat_command_name != "test":
                res = 1
            logger.info('<KO>: %s\n' % error)
    
    # Print the final state
    if res == 0:
        final_status = "OK"
    else:
        final_status = "KO"
        
    msg = "Commands: <%s> (%d/%d)" % (final_status, nb_pass, len(commands))
    logger.info(msg)   
    return RCO.ReturnCode(final_status, msg)
