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
import src.utilsSat as UTS
from src.salomeTools import _BaseCommand

########################################################################
# Command class
########################################################################
class Command(_BaseCommand):
  """
  The job command executes the commands of the job defined
  in the jobs configuration file\
  
  | Examples:
  | >> sat job --jobs_config my_jobs --name my_job"
  """
  
  name = "job"
  
  def getParser(self):
    """Define all options for command 'sat job <options>'"""
    parser = self.getParserWithHelp()
    
    '''version 5.0
    parser.add_option(
        'j', 'jobs_config', 'string', 'jobs_cfg', 
        _('Mandatory: The name of the config file that contains the jobs configuration') )
    parser.add_option(
        '', 'name', 'string', 'job',
        _('Mandatory: The job name from which to execute commands.'), "" )
    return parser
    '''

    # version 5.1 destroy commands job & jobs ambiguity
    parser.add_option(
        'c', 'config', 'string', 'config_jobs', 
        _('Mandatory: The name of the config file that contains the jobs configuration') )
    parser.add_option(
        'j', 'job', 'string', 'job_name',
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
    if not options.config_jobs:
        msg = _("The option --config is required")      
        return RCO.ReturnCode("KO", msg)
    
    # Make sure the name option has been called
    if not options.job_name:
        msg = _("The option --job is required")      
        return RCO.ReturnCode("KO", msg)
    
    # Find the file in the directories
    found = True
    fPyconf = options.config_jobs
    if not file_config_jobs.endswith('.pyconf'): 
        fPyconf += '.pyconf'
        
    for cfg_dir in l_cfg_dir:
        file_config_jobs = os.path.join(cfg_dir, fPyconf)
        if os.path.exists(file_config_jobs):
            found = True
            break

    if not found:
        msg = _("""\
The job file configuration %s was not found.
Use the --list option to get the possible files.""") % UTS.blue(fPyconf)
        return RCO.ReturnCode("KO", msg)
    
    info = [ (_("Platform"), config.VARS.dist),
             (_("File containing the jobs configuration"), file_config_jobs) ]
    logger.info(UTS.formatTuples(info))
    
    # Read the config that is in the file
    config_jobs = UTS.read_config_from_a_file(file_config_jobs)
    
    # Find the job and its commands
    found = False
    for job in config_jobs.jobs:
        if job.name == options.job_name:
            commands = job.commands
            found = True
            break
    if not found:
        msg = _("Impossible to find the job %s in %s") % (options.job_name, file_config_jobs)
        return RCO.ReturnCode("KO", msg)
    
    # Find the maximum length of the commands in order to format the display
    len_max_command = max([len(cmd) for cmd in commands])
    
    # Loop over the commands and execute it
    res = [] # list of results
    for command in commands:
        specific_option = False
        # Determine if it is a sat command or a shell command
        cmd_exe = command.split(" ")[0] # first part
        if cmd_exe == "sat":
            # use the salomeTools parser to get the options of the command
            sat_parser = salomeTools.parser
            input_parser = UTS.remove_item_from_list(command.split(' ')[1:], "")
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

        logger.logStep_begin("Executing %s" % UTS.label(command))
        # Execute the command
        # obsolete tofix new call executeMicroCommand and filterNameAppli...
        # rc = sat_command(end_cmd, options = options, batch = True, verbose = 0, logger_add_link = logger)
        # example of cmd_args
        # cmd_args = "--products %s --build --install" % p_name 
        nameAppli, cmd_args = self.filterNameAppli(end_cmd)
        rc = self.executeMicroCommand(sat_command_name, "", cmd_args)
        res.append(rc)
        logger.logStep_end(rc)
        
    # Print the final state
    good_result = sum(1 for r in res if r.isOk())
    nbExpected = len(commands)
    msgCount = "(%d/%d)" % (good_result, nbExpected)
    if good_result == nbExpected:
      status = "OK"
      msg = _("command job")
      logger.info("\n%s %s: <%s>.\n" % (msg, msgCount, status))
    else:
      status = "KO"
      msg = _("command job, some commands have failed")
      logger.info("\n%s %s: <%s>.\n" % (msg, msgCount, status))

    return RCO.ReturnCode(status, "%s %s" % (msg, msgCount))
    
  def filterNameAppli(self, end_cmd):
    DBG.tofix("sat job filterNameAppli()", end_cmd)
    return "???", end_cmd