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
import sys
import tempfile
import traceback
import csv
import shutil
import itertools
import re

import pprint as PP

# import paramiko later
  
import src.ElementTree as ETREE
import src.debug as DBG
import src.returnCode as RCO
import src.utilsSat as UTS
import src.pyconf as PYCONF
import src.xmlManager as XMLMGR
from src.salomeTools import _BaseCommand
import src.dateTime as DATT

STYLESHEET_GLOBAL = "jobs_global_report.xsl"
STYLESHEET_BOARD = "jobs_board_report.xsl"

DAYS_SEPARATOR = ","
CSV_DELIMITER = ";"

_PARAMIKO = []

def getParamiko(logger=None):
  if len(_PARAMIKO) == 0:
    try:
      import paramiko as PRMK
      _PARAMIKO.append(PRMK)
      if logger is not None: # as native
        msg = "\nparamiko version %s at %s" % \
              (PRMK.__version__, os.path.dirname(PRMK.__file__))
        logger.info(msg)
      return PRMK
    except Exception as e:
      if logger is not None:
        msg = """\
Python paramiko prerequisite not installed.
Jobs on other machines impossible.
try 'pip install paramiko'
"""        
        logger.critical(msg)
      return None
  else:
    return _PARAMIKO[0]
    

########################################################################
# Command class
########################################################################
class Command(_BaseCommand):
  """
  The jobs command command launches maintenances that are described in 
  the dedicated jobs configuration file.

  | Examples:
  | >> # get list of existing config jobs files (pyconf files)
  | >> sat jobs --list
  | >> # launch job1 & job2 defined in my_jobs.pyconf
  | >> sat jobs --configs my_jobs -jobs job1,job2 --publish
  """
  
  name = "jobs"
  
  def getParser(self):
    """Define all options for command 'sat jobs <options>'"""
    parser = self.getParserWithHelp()
    
    '''version 5.0
    parser.add_option(
        'n', 'name', 'list2', 'jobs_cfg', 
        _('Mandatory: The name of the config file that contains the jobs configuration. Can be a list.') )
     parser.add_option(
        'o', 'only_jobs', 'list2', 'only_jobs',
        _('Optional: the list of jobs to launch, by their name.') )   
    '''
        
    # version 5.1 destroy commands job & jobs ambiguity
    parser.add_option(
        'c', 'configs', 'list2', 'configs_jobs', 
        _('Mandatory: The name of the config file(s) that contains the jobs configurations.') )
    parser.add_option(
        'j', 'jobs', 'list2', 'job_names',
        _('Mandatory: The job name(s) from which to execute commands.'), "" )

    parser.add_option(
        'l', 'list', 'boolean', 'list', 
        _('Optional: list all available config files.') )
    parser.add_option(
        't', 'test_connection', 'boolean', 'test_connection',
        _("Optional: try to connect to the machines. Not executing the jobs."),
        False )
    parser.add_option(
        'p', 'publish', 'boolean', 'publish',
        _("Optional: generate an xml file that can be read in a browser to display the jobs status."),
        False )
    parser.add_option(
        'i', 'input_boards', 'string', 'input_boards', 
        _("Optional: the path to csv file that contain the expected boards."),
        "" )
    parser.add_option(
        '', 'completion', 'boolean', 'no_label',
        _("Optional (internal use): do not print labels, Works only with --list."),
        False )
    return parser

  def run(self, cmd_arguments):
    """method called for command 'sat jobs <options>'"""
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
    
    # list option : display all the available config files
    if options.list:
      msg = ""
      for cfg_dir in l_cfg_dir:
        if not options.no_label:
            msg += UTS.info("\n------ %s\n" % cfg_dir)
        if not os.path.exists(cfg_dir):
            continue
        for f in sorted(os.listdir(cfg_dir)):
            if not f.endswith('.pyconf'):
                continue
            cfilename = f[:-7]
            msg += ("%s\n" % cfilename)
      logger.info(msg)
      return RCO.ReturnCode("OK", "jobs command --list done")

    # Make sure the jobs_config option has been called
    if not options.configs_jobs:
        msg = _("The option --jobs_config is required")      
        logger.error(msg)
        return RCO.ReturnCode("KO", msg)
    
    # Find the file in the directories, unless it is a full path
    # merge all in a config
    merger = PYCONF.ConfigMerger()
    config_jobs = PYCONF.Config()
    l_conf_files_path = []
    for config_file in options.configs_jobs:
        found, file_configs_jobs = get_config_file_path(config_file, l_cfg_dir)
        if not found:
            msg = _("""\
The file configuration %s was not found.
Use the --list option to get the possible files.""") % config_file
            logger.error(msg)
            return RCO.ReturnCode("KO", msg)
        l_conf_files_path.append(file_configs_jobs)
        # Read the config that is in the file
        one_config_jobs = UTS.read_config_from_a_file(file_configs_jobs)
        merger.merge(config_jobs, one_config_jobs)
    
    msg = "\n" + _("Platform = ") + config.VARS.dist
    msg += "\n%s =\n%s" % \
           ( _("Files containing the jobs configuration"), 
            PP.pformat(l_conf_files_path) )   
    logger.info(msg)

    if options.job_names:
      l_jb = PYCONF.Sequence()
      for jb in config_jobs.jobs:
          if jb.name in options.job_names:
              l_jb.append(jb, "Job that was given in job_names option parameters")
      config_jobs.jobs = l_jb
    
    # Parse the config jobs in order to develop all the factorized jobs
    develop_factorized_jobs(config_jobs)
    
    # Make a unique file that contain all the jobs in order to use it 
    # on every machine
    name_pyconf = "_".join([os.path.basename(path)[:-len('.pyconf')] 
                            for path in l_conf_files_path]) + ".pyconf"
    path_pyconf = UTS.get_tmp_filename(config, name_pyconf)
    #Save config
    with open(path_pyconf , 'w') as f:
      config_jobs.__save__(f)
    
    # log the paramiko messages and problems
    log_dir = UTS.get_log_path(config)
    logger.info("jobs log directory = %s" % UTS.info(log_dir))
    
    paramiko = getParamiko(logger)
    if paramiko == None:
      return RCO.ReturnCode("KO", "paramiko prerequisite not installed")

    # paramiko.util.log_to_file(os.path.join(paramiko_log_dir_path, logger.txtFileName))
    rc = logger.setLoggerParamiko() # manages configuration of paramiko logger

    loggerPrmk = logger.getLoggerParamiko()
    logger.info("paramiko logger %s" % rc)
    loggerPrmk.info("initial message from sat jobs options\n%s" % options)
      
    # Initialization
    today_jobs = Jobs(runner, logger, path_pyconf, config_jobs)
    
    # SSH connection to all machines
    logger.info("today jobs machines =\n%s" % PP.pformat([m.host for m in today_jobs.lmachines]))
    res = today_jobs.ssh_connection_all_machines()
    if options.test_connection:
      return RCO.ReturnCodeFromList(res)
    
    gui = None
    if options.publish:
        logger.debug(_("Initialize the xml boards : "))

        # Copy the stylesheets in the log directory 
        log_dir = log_dir
        xsl_dir = os.path.join(config.VARS.srcDir, 'xsl')
        files_to_copy = []
        files_to_copy.append(os.path.join(xsl_dir, STYLESHEET_GLOBAL))
        files_to_copy.append(os.path.join(xsl_dir, STYLESHEET_BOARD))
        files_to_copy.append(os.path.join(xsl_dir, "command.xsl"))
        files_to_copy.append(os.path.join(xsl_dir, "running.gif"))
        for file_path in files_to_copy:
            # OP We use copy instead of copy2 to update the creation date
            #    So we can clean the LOGS directories easily
            shutil.copy(file_path, log_dir)
        
        # Instanciate the Gui in order to produce the xml files that contain all
        # the boards
        gui = Gui(log_dir,
                  today_jobs.ljobs,
                  today_jobs.ljobs_not_today,
                  config.VARS.datehour,
                  logger,
                  file_boards = options.input_boards)
        
        logger.debug("Gui init <OK>")
        
        # Display the list of the xml files
        logger.info(("List of published files:\n%s") % gui.xml_global_file.logFile)
        msg = ""
        for board in gui.d_xml_board_files.keys():
            file_path = gui.d_xml_board_files[board].logFile
            file_name = os.path.basename(file_path)
            msg += "%s\n" % file_path
            logger.add_link(file_name, "board", 0, board)
              
        logger.info(msg)
        
    today_jobs.gui = gui
    
    interruped = False
    try:
        # Run all the jobs contained in config_jobs
        today_jobs.run_jobs()
    except KeyboardInterrupt:
        interruped = True
        logger.critical(UTS.red(_("KeyboardInterrupt forced interruption")))
    except Exception as e:
         # verbose debug message with traceback
        msg = _("Exception raised, the jobs loop has been interrupted:\n\n%s")
        logger.critical(msg % UTS.yellow(traceback.format_exc()))    
    finally:
        # make clear kill subprocess
        res = RCO.ReturnCode("OK", "jobs command finally done")
        if interruped:
            msg = _("Killing the running jobs and trying to get the corresponding logs\n")
            logger.warning(UTS.red(msg))
            res = RCO.ReturnCode("KO", msg)
            
        # find the potential not finished jobs and kill them
        for jb in today_jobs.ljobs:
            if not jb.has_finished():
                res += RCO.ReturnCode("KO", "job %s has not finished" % jb.name)
                try:
                    jb.kill_remote_process()
                except Exception as e:
                    msg = _("Failed to kill job %s: %s\n") % (jb.name, e)
                    logger.warning(UTS.red(msg))
                    res += RCO.ReturnCode("KO", msg)
            if jb.res_job != "0":
                res += RCO.ReturnCode("KO", "job %s fail" % jb.name)
        if interruped:
            if today_jobs.gui:
                today_jobs.gui.last_update(_("Forced interruption"))
        else:
            if today_jobs.gui:
                today_jobs.gui.last_update()
        # Output the results
        today_jobs.write_all_results()
        # Remove the temporary pyconf file
        if os.path.exists(path_pyconf):
            os.remove(path_pyconf)
        return res
  

class Machine(object):
    """
    Manage a ssh connection on a machine
    """
    def __init__(self,
                 name,
                 host,
                 user,
                 port=22,
                 passwd=None,
                 sat_path="salomeTools"):
        self.name = name
        self.host = host
        self.port = port
        self.distribution = None # Will be filled after copying SAT on the machine
        self.user = user
        self.password = passwd
        self.sat_path = sat_path
        self.paramiko = getParamiko()
        self.ssh = self.paramiko.SSHClient()
        self._connection_successful = None
    
    def connect(self):
        """Initiate the ssh connection to the remote machine
        
        :param logger: (Logger) The logger instance 
        :return: (RCO.ReturnCode) OK/KO and why as message
        """

        self._connection_successful = False
        self.ssh.load_system_host_keys()
        self.ssh.set_missing_host_key_policy(self.paramiko.AutoAddPolicy())
        aDict = {
          "name": self.name,
          "host": self.host,
          "port": self.port,
          "distrib": self.distribution, # Will be filled after copying SAT on the machine
          "user": self.user,
          "password": self.password,
          "sat_path": self.sat_path,
        }
        DBG.write("ssh.connect", aDict)
        try:
          res = self.ssh.connect(self.host, port=self.port, username=self.user, password = self.password)
        except Exception as e:
          msg = "connecting SSH on %s as %s" % (self.host, str(e))
          rc = RCO.ReturnCode("KO", msg, e) # e for futur more explicit...
          return rc
        DBG.write("ssh.connect OK", res)
        self._connection_successful = True
        rc = RCO.ReturnCode("OK", "connecting SSH done on %s" % self.host, aDict)
        return rc
        
    
    def successfully_connected(self, logger):
        """
        Verify if the connection to the remote machine has succeed
        
        :param logger: The logger instance 
        :return: (RCO.ReturnCode) OK/KO and why as message
        """
        if self._connection_successful == None:
            msg = _("""\
Ask if the connection
(name: %(1)s host: %(2)s, port: %(3)s, user: %(4)s) is OK
whereas there were no connection request""" % \
   {"1": self.name, "2": self.host, "3": self.port, "4": self.user} )
            logger.critical(UTS.red(msg))
        return self._connection_successful

    def copy_sat(self, sat_local_path, job_file):
        """
        Copy salomeTools to the remote machine in self.sat_path
        
        :return: (RCO.ReturnCode) OK/KO and why as message
        """
        try:
            # open a sftp connection
            self.sftp = self.ssh.open_sftp()
            # Create the sat directory on remote machine if it is not existing
            self.mkdir(self.sat_path, ignore_existing=True)
            # Put sat
            self.put_dir(sat_local_path, self.sat_path, filters = ['.git'])
            # put the job configuration file in order to make it reachable 
            # on the remote machine
            remote_job_file_name = ".%s" % os.path.basename(job_file)
            self.sftp.put(job_file, os.path.join(self.sat_path, remote_job_file_name))
            res = RCO.ReturnCode("OK", "copy sat done on %s" % self.host)
        except Exception as e:
            res = RCO.ReturnCode("KO", "copy sat problem on %s\n%s" % (self.host, str(e)))
            self._connection_successful = False
        
        return res
        
    def put_dir(self, source, target, filters = []):
        """
        Uploads the contents of the source directory to the target path.
        The target directory needs to exists. 
        All sub-directories in source are created under target.
        """
        for item in os.listdir(source):
            if item in filters:
                continue
            source_path = os.path.join(source, item)
            destination_path = os.path.join(target, item)
            if os.path.islink(source_path):
                linkto = os.readlink(source_path)
                try:
                    self.sftp.symlink(linkto, destination_path)
                    self.sftp.chmod(destination_path,
                                    os.stat(source_path).st_mode)
                except IOError:
                    pass
            else:
                if os.path.isfile(source_path):
                    self.sftp.put(source_path, destination_path)
                    self.sftp.chmod(destination_path,
                                    os.stat(source_path).st_mode)
                else:
                    self.mkdir(destination_path, ignore_existing=True)
                    self.put_dir(source_path, destination_path)

    def mkdir(self, path, mode=511, ignore_existing=False):
        """
        As mkdir by adding an option to not fail if the folder exists 
        """
        try:
            self.sftp.mkdir(path, mode)
        except IOError:
            if ignore_existing:
                pass
            else:
                raise       
    
    def exec_command(self, command, logger):
        """Execute the command on the remote machine
        
        :param command: (str) The command to be run
        :param logger: The logger instance 
        :return: (paramiko.channel.ChannelFile, etc) 
          the stdin, stdout, and stderr of the executing command,
          as a 3-tuple
        """
        import traceback
        try:        
            # Does not wait the end of the command
            (stdin, stdout, stderr) = self.ssh.exec_command(command)
        except self.paramiko.SSHException:
            msg = _("<KO>: the paramiko server failed to execute the command\n")
            msg += "command: '%s'\n" % command
            msg += "\n%s\n" % UTS.yellow(traceback.format_exc())
            logger.critical(msg)
            return (None, None, None)
        except Exception as e:
            msg = _("<KO>: an exception raised on ssh.exec_command:\n")
            msg += "command: '%s'\n" % command
            msg += "\n%s\n" % UTS.yellow(traceback.format_exc())
            logger.critical(msg)
            return (None, None, None)
        return (stdin, stdout, stderr)

    def close(self):
        """Close the ssh connection"""
        self.ssh.close()
     
    def write_info(self, logger):
        """
        Prints the informations relative to the machine in the logger 
        (terminal traces and log file)
        
        :param logger: The logger instance
        :return: None
        """
        if self.successfully_connected(logger):
            msg = "<OK>"
        else:
            msg = "<KO>"
        msg += "host: %s, " % self.host
        msg += "port: %s, " % str(self.port)
        msg += "user: %s" % str(self.user)
        logger.info("Connection %s" % msg ) 


class Job(object):
    """
    Class to manage one job
    """
    def __init__(self,
                 name,
                 machine,
                 application,
                 board, 
                 commands,
                 timeout,
                 config,
                 job_file_path,
                 logger,
                 after=None,
                 prefix=None):

        self.name = name
        self.machine = machine
        self.after = after
        self.timeout = timeout
        self.application = application
        self.board = board
        self.config = config
        self.logger = logger
        # The list of log files to download from the remote machine 
        self.remote_log_files = []
        
        # The remote command status
        # -1 means that it has not been launched, 
        # 0 means success and 1 means fail
        self.res_job = "-1"
        self.cancelled = False
        
        self._T0 = DATT.DateTime()
        self._Tf = DATT.DateTime()
        self._has_begun = False
        self._has_finished = False
        self._has_timouted = False
        self._stdin = None # Store the command inputs field
        self._stdout = None # Store the command outputs field
        self._stderr = None # Store the command errors field

        self.out = ""
        self.err = ""
        
        self.name_remote_jobs_pyconf = ".%s" % os.path.basename(job_file_path)
        self.commands = commands
        sat_path = self.machine.sat_path
        sat = os.path.join(sat_path, "sat")
        cmd = sat + " -l %s job --config %s --job %s"
        self.command = cmd % \
                     ( os.path.join(sat_path, "list_log_files.txt"),
                       os.path.join(sat_path, self.name_remote_jobs_pyconf),
                       self.name )
        if prefix:
            self.command = prefix + ' "' + self.command +'"'
    
    def get_pids(self):
        """
        Get the pid(s) corresponding to the command that have been launched
        On the remote machine
        
        :return: (list) The list of integers corresponding to the found pids
        """
        pids = []
        cmd_pid = 'ps aux | grep "' + self.command + '" | awk \'{print $2}\''
        (_, out_pid, _) = self.machine.exec_command(cmd_pid, self.logger)
        pids_cmd = out_pid.readlines()
        pids_cmd = [str(UTS.only_numbers(pid)) for pid in pids_cmd]
        pids += pids_cmd
        return pids
    
    def kill_remote_process(self, wait=1):
        """Kills the process on the remote machine.
        
        :return: (str, str) the output of the kill, the error of the kill
        """
        try:
            pids = self.get_pids()
        except:
            return ("Unable to get the pid of the command.", "")
            
        cmd_kill = " ; ".join([("kill -2 " + pid) for pid in pids])
        (_, out_kill, err_kill) = self.machine.exec_command(cmd_kill, self.logger)
        DATT.sleep(wait)
        return (out_kill.read().decode(), err_kill.read().decode())
            
    def has_begun(self):
        """Returns True if the job has already begun
        
        :return: (bool) True if the job has already begun
        """
        return self._has_begun
    
    def has_finished(self):
        """
        Returns True if the job has already finished 
        (i.e. all the commands have been executed)
        If it is finished, the outputs are stored in the fields out and err.
        
        :return: (bool) True if the job has already finished
        """
        
        # If the method has already been called and returned True
        if self._has_finished:
            return True
        
        # If the job has not begun yet
        if not self.has_begun():
            return False
        
        if self._stdout.channel.closed:
            self._has_finished = True
            # Store the result outputs
            self.out += self._stdout.read().decode()
            self.err += self._stderr.read().decode()
            # Put end time
            self._Tf = DATT.DateTime("now")
            # And get the remote command status and log files
            try:
                self.get_log_files()
            except Exception as e:
                self.err += _("Unable to get remote log files: %s") % e
        
        return self._has_finished
          
    def get_log_files(self):
        """
        Get the log files produced by the command launched 
        on the remote machine, and put it in the log directory of the user,
        so they can be accessible from 
        """
        # Do not get the files if the command is not finished
        if not self.has_finished():
            msg = _("Trying to get log files whereas the job is not finished.")
            self.logger.warning(UTS.red(msg))
            return
        
        # First get the file that contains the list of log files to get
        tmp_file_path = UTS.get_tmp_filename(self.config, "list_log_files.txt")
        remote_path = os.path.join(self.machine.sat_path, "list_log_files.txt")
        self.machine.sftp.get(remote_path, tmp_file_path)
        
        # Read the file and get the result of the command and all the log files
        # to get
        fstream_tmp = open(tmp_file_path, "r")
        file_lines = fstream_tmp.readlines()
        file_lines = [line.replace("\n", "") for line in file_lines]
        fstream_tmp.close()
        os.remove(tmp_file_path)
        
        try :
            # The first line is the result of the command (0 success or 1 fail)
            self.res_job = file_lines[0]
        except Exception as e:
            self.err += _("Unable to get status from remote file '%(1)s': %(2)s") % \
                        {"1": remote_path, "2": str(e)}

        for i, job_path_remote in enumerate(file_lines[1:]):
            try:
                # For each command, there is two files to get :
                # 1- The xml file describing the command and giving the 
                # internal traces.
                # 2- The txt file containing the system command traces (like 
                # traces produced by the "make" command)
                # 3- In case of the test command, there is another file to get :
                # the xml board that contain the test results
                dirname = os.path.basename(os.path.dirname(job_path_remote))
                if dirname != 'OUT' and dirname != 'TEST':
                    # Case 1-
                    local_path = os.path.join(os.path.dirname(
                                                        self.logger.logFilePath),
                                              os.path.basename(job_path_remote))
                    if i==0: # The first is the job command
                        self.logger.add_link(os.path.basename(job_path_remote),
                                             "job",
                                             self.res_job,
                                             self.command) 
                elif dirname == 'OUT':
                    # Case 2-
                    local_path = os.path.join(os.path.dirname(
                                                        self.logger.logFilePath),
                                              'OUT',
                                              os.path.basename(job_path_remote))
                elif dirname == 'TEST':
                    # Case 3-
                    local_path = os.path.join(os.path.dirname(
                                                        self.logger.logFilePath),
                                              'TEST',
                                              os.path.basename(job_path_remote))
                
                # Get the file
                if not os.path.exists(local_path):
                    self.machine.sftp.get(job_path_remote, local_path)
                self.remote_log_files.append(local_path)
            except Exception as e:
                self.err += _("Unable to get %(1)s log file from remote: %(2)s") % \
                            {"1": str(job_path_remote), "2": str(e)}

    def has_failed(self):
        """
        Returns True if the job has failed. 
        A job is considered as failed if the machine could not be reached,
        if the remote command failed, 
        or if the job finished with a time out.
        
        :return: (bool) True if the job has failed
        """
        if not self.has_finished():
            return False
        if not self.machine.successfully_connected(self.logger):
            return True
        if self.is_timeout():
            return True
        if self.res_job == "1":
            return True
        return False
    
    def cancel(self):
        """
        In case of a failing job, one has to cancel every job that depend on it.
        This method put the job as failed and will not be executed.
        """
        if self.cancelled:
            return
        self._has_begun = True
        self._has_finished = True
        self.cancelled = True
        msg = _("This job was not launched because its father has failed.")
        self.out += msg
        self.err += msg

    def is_running(self):
        """Returns True if the job commands are running 
        
        :return: (bool) True if the job is running
        """
        return self.has_begun() and not self.has_finished()

    def is_timeout(self):
        """Returns True if the job commands has finished with timeout 
        
        :return:  (bool) True if the job has finished with timeout
        """
        return self._has_timouted

    def time_elapsed(self):
        """Get the time elapsed since the job launching
        
        :return: The number of seconds
        :rtype: int
        """
        if not self.has_begun():
            return -1
        delta = self._T0.getSecondsToNow()
        return delta
    
    def check_time(self):
        """
        Verify that the job has not exceeded its timeout.
        If it has, kill the remote command and consider the job as finished.
        """
        if not self.has_begun():
            return
        if self.time_elapsed() > self.timeout:
            self._has_finished = True
            self._has_timouted = True
            self._Tf = DATT.DateTime("now")
            (out_kill, __) = self.kill_remote_process()
            self.out += "TIMEOUT \n" + out_kill
            self.err += "TIMEOUT : %s seconds elapsed\n" % str(self.timeout)
            try:
                self.get_log_files()
            except Exception as e:
                self.err += _("Unable to get remote log files!\n%s\n" % str(e))
                    
    def run(self):
        """
        Launch the job by executing the remote command.
        """
        
        # Prevent multiple run
        if self.has_begun():
            msg = _("A job can only be launched one time")
            msg2 = _("Trying to launch the job '%s' whereas it has already been launched.") % self.name
            self.logger.warning( UTS.red("%s\n%s\n" % (msg,msg2)) )
            return RCO.ReturnCode("KO", msg2)
        
        # Do not execute the command if the machine could not be reached
        if not self.machine.successfully_connected(self.logger):
            self._has_finished = True
            self.out = "N\A"
            self.err += ("Connection to machine (name : %s, host: %s, port:"
                        " %s, user: %s) has failed\nUse the log command "
                        "to get more information."
                        % (self.machine.name,
                           self.machine.host,
                           self.machine.port,
                           self.machine.user))
        else:
            # Usual case : Launch the command on remote machine
            self._T0 = DATT.DateTime("now")
            self._stdin, self._stdout, self._stderr = self.machine.exec_command(
                                                                  self.command,
                                                                  self.logger)
            # If the results are not initialized, finish the job
            if (self._stdin, self._stdout, self._stderr) == (None, None, None):
                self._has_finished = True
                self._Tf = DATT.DateTime("now")
                self.out += "N\A"
                self.err += "The server failed to execute the command"
        
        # Put the beginning flag to true.
        self._has_begun = True
    
    def write_results(self):
        """
        Display on the terminal all the job's information
        """
        msg = "name : %s\n" % self.name
        if self.after: 
          msg += "after : %s\n" % self.after
        delta = DATT.DeltaTime(self._T0, self._Tf)
        msg += "Time elapsed : %s\n" % delta.toStrHuman()
        msg += "Begin time   : %s\n" % self._T0.toStrHuman()
        msg += "End time     : %s\n\n" % self._Tf.toStrHuman()
        
        self.logger.info(msg)
        
        machine_head = "Informations about connection :\n"
        underline = (len(machine_head) - 2) * "-"
        self.logger.info(machine_head+underline)
        self.machine.write_info(self.logger)
        
        msg = "out : \n"
        if self.out == "":
            msg += "Unable to get output\n"
        else:
            msg += self.out + "\n"
        msg += "err :\n%s\n" % self.err
        self.logger.info(msg)
        
    def get_status(self):
        """Get the status of the job (used by the Gui for xml display)
        
        :return: (str) The current status of the job
        """
        if not self.machine.successfully_connected(self.logger):
            return "SSH connection KO"
        if not self.has_begun():
            return "Not launched"
        if self.cancelled:
            return "Cancelled"
        if self.is_running():
            return "running since " + self._T0.toStrHuman()       
        if self.has_finished():
            if self.is_timeout():
                return "Timeout since " + self._Tf.toStrHuman() 
            return "Finished since " + self._Tf.toStrHuman() 
    
class Jobs(object):
    """
    Class to manage the jobs to be run
    """
    def __init__(self,
                 runner,
                 logger,
                 job_file_path,
                 config_jobs,
                 length_columns = 20):
        # The jobs configuration
        self.cfg_jobs = config_jobs
        self.job_file_path = job_file_path
        # The machine that will be used today
        self.lmachines = []
        # The list of machine (hosts, port) that will be used today 
        # (a same host can have several machine instances since there 
        # can be several ssh parameters) 
        self.lhosts = []
        # The jobs to be launched today 
        self.ljobs = []
        # The jobs that will not be launched today
        self.ljobs_not_today = []
        self.runner = runner
        self.logger = logger
        self.len_columns = length_columns
        
        # the list of jobs that have not been run yet
        self._l_jobs_not_started = []
        # the list of jobs that have already ran 
        self._l_jobs_finished = []
        # the list of jobs that are running 
        self._l_jobs_running = [] 
                
        self.determine_jobs_and_machines()
    
    def define_job(self, job_def, machine):
        """
        Takes a pyconf job definition and a machine (from class machine)
        and returns the job instance corresponding to the definition.
        
        :param job_def: (Mapping a job definition 
        :param machine: (Machine) the machine on which the job will run
        :return: (Job) The corresponding job in a job class instance
        """
        name = job_def.name
        cmmnds = job_def.commands
        if not "timeout" in job_def:
            timeout = 4*60*60 # default timeout = 4h
        else:
            timeout = job_def.timeout
        after = None
        if 'after' in job_def:
            after = job_def.after
        application = None
        if 'application' in job_def:
            application = job_def.application
        board = None
        if 'board' in job_def:
            board = job_def.board
        prefix = None
        if "prefix" in job_def:
            prefix = job_def.prefix
            
        return Job(name,
                   machine,
                   application,
                   board,
                   cmmnds,
                   timeout,
                   self.runner.getConfig(),
                   self.job_file_path,
                   self.logger,
                   after = after,
                   prefix = prefix)
    
    def determine_jobs_and_machines(self):
        """
        Reads the pyconf jobs definition and instantiates all
        the machines and jobs to be done today.

        :return: None
        """
        today = DATT.getWeekDayNow()
        host_list = []
               
        for job_def in self.cfg_jobs.jobs :
                
            if not "machine" in job_def:
                msg = _("""\
The job '%s' do not have the key 'machine'.
This job is ignored.
""") % job_def.name
                self.logger.warning(msg)
                continue
            name_machine = job_def.machine
            
            a_machine = None
            for mach in self.lmachines:
                if mach.name == name_machine:
                    a_machine = mach
                    break
            
            config = self.runner.getConfig()
            if a_machine == None:
                for machine_def in self.cfg_jobs.machines:
                    if machine_def.name == name_machine:
                        if 'host' not in machine_def:
                            host = config.VARS.hostname
                        else:
                            host = machine_def.host

                        if 'user' not in machine_def:
                            user = config.VARS.user
                        else:
                            user = machine_def.user

                        if 'port' not in machine_def:
                            port = 22
                        else:
                            port = machine_def.port
            
                        if 'password' not in machine_def:
                            passwd = None
                        else:
                            passwd = machine_def.password    
                            
                        if 'sat_path' not in machine_def:
                            sat_path = "salomeTools"
                        else:
                            sat_path = machine_def.sat_path
                        
                        a_machine = Machine(
                                            machine_def.name,
                                            host,
                                            user,
                                            port=port,
                                            passwd=passwd,
                                            sat_path=sat_path
                                            )
                        
                        self.lmachines.append(a_machine)
                        if (host, port) not in host_list:
                            host_list.append((host, port))
                
                if a_machine == None:
                    msg = _("""\
The job '%(job)s' requires the machine '%(machine)s'.
This machine is not defined in the configuration file.
The job will not be launched.
""") % {"job" : job_def.name, "machine" : name_machine}
                    self.logger.warning(msg)
                    continue
                                  
            a_job = self.define_job(job_def, a_machine)
                
            if today in job_def.when:    
                self.ljobs.append(a_job)
            else: # today in job_def.when
                self.ljobs_not_today.append(a_job)
               
        self.lhosts = host_list
        
    def ssh_connection_all_machines(self):
        """Do the ssh connection to every machine to be used today.

        :return: None
        """
        config = self.runner.getConfig()
        logger = self.logger
        logger.info("\nEstablishing connection with all the machines:")
        tabul = 40
        
        res = [] # all connections
        for machine in self.lmachines:
            # little algorithm in order to display traces
            header = ("Connection to %s" % machine.name)
            step = "SSH connection"
            logger.logStep_begin(header, step)
            # the call to the method that initiate the ssh connection
            rc = machine.connect()
            if not rc.isOk():
              logger.logStep_end(rc, tabul)
              continue
            
            # Copy salomeTools to the remote machine
            if machine.successfully_connected(logger): # as rc.isOk()
                step = _("Remove SAT")
                logger.logStep(step)
                (__, out_dist, __) = machine.exec_command(
                            "rm -rf %s" % machine.sat_path, logger)
                out_dist.read()
                
                step = _("Copy SAT")
                logger.logStep(step)

                rc = machine.copy_sat(config.VARS.salometoolsway, self.job_file_path)
                logger.logStep(str(rc))
                
                if rc.isOk():
                  # set the local settings of sat on the remote machine using the init command
                  sat = os.path.join(machine.sat_path, "sat")
                  cmd = sat + " init --base default --workdir  default --log_dir default"
                  (__, out_dist, __) = machine.exec_command(cmd, logger)
                  out_dist.read()    
                  
                  # get the remote machine distribution using a sat command
                  cmd = sat + " config --value VARS.dist" 
                  (__, out_dist, __) = machine.exec_command(cmd, logger)
                  # machine.distribution = out_dist.read().decode().replace("\n", "")
                  rc = self.extractIn(out_dist.read(), "dist: ")
                  if rc.isOk():
                    machine.distribution = rc.getValue()
                  rc = RCO.ReturnCode("OK", "remote distribution %s" % machine.distribution)
                
            # end of one machine
            res.append(rc)
            # Print the status of the copy
            logger.logStep_end(str(rc), tabul)
                
        return res
        
    def extractIn(self, inStr, searchStr):
      """
      find in multiples lines value at left of searchStr
      return at first line OK
      """
      out = inStr.decode().split("\n")
      for line in out:
        if searchStr in line:
          res = line.split(searchStr)[1]
          return RCO.ReturnCode("OK", "'%s' found as '%s'" % (searchStr, res), res)
      return RCO.ReturnCode("KO", "'%s' not found in %s" % (searchStr, out))
        

    def is_occupied(self, hostname):
        """
        Returns True if a job is running on 
        the machine defined by its host and its port.
        
        :param hostname: (str, int) the pair (host, port)
        :return: (Job or bool) 
          the job that is running on the host, 
          or false if there is no job running on the host. 
        """
        host = hostname[0]
        port = hostname[1]
        for jb in self.ljobs:
            if jb.machine.host == host and jb.machine.port == port:
                if jb.is_running():
                    return jb
        return False
    
    def update_jobs_states_list(self):
        """
        Updates the lists that store the currently
        running jobs and the jobs that have already finished.
        
        :return: (bool) nb_job_finished_now > nb_job_finished_before
        """
        jobs_finished_list = []
        jobs_running_list = []
        for jb in self.ljobs:
            if jb.is_running():
                jobs_running_list.append(jb)
                jb.check_time()
            if jb.has_finished():
                jobs_finished_list.append(jb)
        
        nb_job_finished_before = len(self._l_jobs_finished)
        self._l_jobs_finished = jobs_finished_list
        self._l_jobs_running = jobs_running_list
        
        nb_job_finished_now = len(self._l_jobs_finished)
        
        return nb_job_finished_now > nb_job_finished_before
    
    def cancel_dependencies_of_failing_jobs(self):
        """Cancels all the jobs that depend on a failing one.
        
        :return: None
        """
        for job in self.ljobs:
            if job.after is None:
                continue
            father_job = self.find_job_that_has_name(job.after)
            if father_job is not None and father_job.has_failed():
                job.cancel()
    
    def find_job_that_has_name(self, name):
        """Returns the job by its name.
        
        :param name: (str) a job name
        :return: (Job) the job that has the name, else None 
        """
        for jb in self.ljobs:
            if jb.name == name:
                return jb
        # the following is executed only if the job was not found
        return None
    
    def str_of_length(self, text, length):
        """
        Takes a string text of any length and returns 
        the most close string of length "length".
        
        :param text: (str) any string
        :param length: (int) a length for the returned string
        :return: (str) the most close string of length "length"
        """
        if len(text) > length:
            text_out = text[:length-3] + '...'
        else:
            diff = length - len(text)
            before = " " * (diff//2)
            after = " " * (diff//2 + diff%2)
            text_out = before + text + after
            
        return text_out
    
    def display_status(self, len_col):
        """
        Takes a length and construct the display of the current status 
        of the jobs in an array that has a column for each host.
        It displays the job that is currently running on the host of the column.
        
        :param len_col: (int) the size of the column 
        :return: None
        """  
        display_line = ""
        for host_port in self.lhosts:
            jb = self.is_occupied(host_port)
            if not jb: # nothing running on the host
                empty = self.str_of_length("empty", len_col)
                display_line += "|" + empty 
            else:
                display_line += "|" + UTS.info(
                                        self.str_of_length(jb.name, len_col))
        
        self.logger.info("\r" + display_line + "|")
    

    def run_jobs(self):
        """
        The main method. Runs all the jobs on every host. 
        For each host, at a given time, only one job can be running.
        The jobs that have the field after (that contain the job that has
        to be run before it) are run after the previous job.
        This method stops when all the jobs are finished.
        
        :return: None
        """
        # Print header
        self.logger.info(_('Executing the jobs :\n'))
        text_line = ""
        for host_port in self.lhosts:
            host = host_port[0]
            port = host_port[1]
            if port == 22: # default value
                text_line += "|" + self.str_of_length(host, self.len_columns)
            else:
                text_line += "|" + self.str_of_length(
                                "("+host+", "+str(port)+")", self.len_columns)
        
        tiret_line = " " + "-"*(len(text_line)-1) + "\n"
        self.logger.info(tiret_line + text_line + "|\n" + tiret_line)
        
        # The infinite loop that runs the jobs
        l_jobs_not_started = UTS.deepcopy_list(self.ljobs)
        while len(self._l_jobs_finished) != len(self.ljobs):
            new_job_start = False
            for host_port in self.lhosts:
                
                if self.is_occupied(host_port):
                    continue
             
                for jb in l_jobs_not_started:
                    if (jb.machine.host, jb.machine.port) != host_port:
                        continue 
                    if jb.after == None:
                        jb.run()
                        l_jobs_not_started.remove(jb)
                        new_job_start = True
                        break
                    else:
                        jb_before = self.find_job_that_has_name(jb.after)
                        if jb_before is None:
                            jb.cancel()
                            msg = _("This job was not launched because its "
                                    "father is not in the jobs list.")
                            jb.out = msg
                            jb.err = msg
                            break
                        if jb_before.has_finished():
                            jb.run()
                            l_jobs_not_started.remove(jb)
                            new_job_start = True
                            break
            self.cancel_dependencies_of_failing_jobs()
            new_job_finished = self.update_jobs_states_list()
            
            if new_job_start or new_job_finished:
                if self.gui:
                    self.gui.update_xml_files(self.ljobs)            
                # Display the current status     
                self.display_status(self.len_columns)
            
            # Make sure that the proc is not entirely busy
            DATT.sleep(0.001)
        
        self.logger.info("\n" + tiret_line + "\n\n")
        
        if self.gui:
            self.gui.update_xml_files(self.ljobs)
            self.gui.last_update()

    def write_all_results(self):
        """Display all the jobs outputs.
        
        :return: None
        """
        for jb in self.ljobs:
            self.logger.info("#------- Results for job %s -------#\n" % jb.name)
            jb.write_results()
            self.logger.info("\n\n")

class Gui(object):
    """
    Class to manage the the xml data that can be displayed in a browser 
    to see the jobs states
    """
    def __init__(self,
                 xml_dir_path,
                 l_jobs,
                 l_jobs_not_today,
                 prefix,
                 logger,
                 file_boards=""):
        """Initialization
        
        :param xml_dir_path: (str) 
          The path to the directory where to put the xml resulting files
        :param l_jobs: (list) the list of jobs that run today
        :param l_jobs_not_today: (list) 
          the list of jobs that do not run today
        :param file_boards: (str) 
          the file path from which to read the expected boards
        """
        # The logging instance
        self.logger = logger
        
        # The prefix to add to the xml files : date_hour
        self.prefix = prefix
        
        # The path of the csv files to read to fill the expected boards
        self.file_boards = file_boards
        
        if file_boards != "":
            today = DATT.getWeekDayNow()
            self.parse_csv_boards(today)
        else:
            self.d_input_boards = {}
        
        # The path of the global xml file
        self.xml_dir_path = xml_dir_path
        # Initialize the xml files
        self.global_name = "global_report"
        xml_global_path = os.path.join(self.xml_dir_path,
                                       self.global_name + ".xml")
        self.xml_global_file = XMLMGR.XmlLogFile(xml_global_path, "JobsReport")

        # Find history for each job
        self.history = {}
        self.find_history(l_jobs, l_jobs_not_today)

        # The xml files that corresponds to the boards.
        # {name_board : xml_object}}
        self.d_xml_board_files = {}

        # Create the lines and columns
        self.initialize_boards(l_jobs, l_jobs_not_today)

        # Write the xml file
        self.update_xml_files(l_jobs)
    
    def add_xml_board(self, name):
        """
        Add a board to the board list
        
        :param name: (str) the board name
        """
        xml_board_path = os.path.join(self.xml_dir_path, name + ".xml")
        aXml = XMLMGR.XmlLogFile(xml_board_path,"JobsReport")
        aXml.add_simple_node_root("distributions")
        aXml.add_simple_node_root("applications")
        aXml.add_simple_node_root("board", text=name)
        self.d_xml_board_files[name] = aXml
           
    def initialize_boards(self, l_jobs, l_jobs_not_today):
        """
        Get all the first information needed for each file and write the 
        first version of the files 
        
        :param l_jobs: (list) the list of jobs that run today
        :param l_jobs_not_today: (list) the list of jobs that do not run today
        """
        # Get the boards to fill and put it in a dictionary
        # {board_name : xml instance corresponding to the board}
        for job in l_jobs + l_jobs_not_today:
            board = job.board
            if (board is not None and 
                                board not in self.d_xml_board_files.keys()):
                self.add_xml_board(board)
        
        # Verify that the boards given as input are done
        for board in list(self.d_input_boards.keys()):
            if board not in self.d_xml_board_files:
                self.add_xml_board(board)
            root_node = self.d_xml_board_files[board].xmlroot
            XMLMGR.append_node_attrib(root_node, {"input_file" : self.file_boards})
        
        # Loop over all jobs in order to get the lines and columns for each 
        # xml file
        d_dist = {}
        d_application = {}
        for board in self.d_xml_board_files:
            d_dist[board] = []
            d_application[board] = []
            
        l_hosts_ports = []
        
        ASNODE = XMLMGR.add_simple_node # shortcut to add a child node to another node
            
        for job in l_jobs + l_jobs_not_today:
            
            if (job.machine.host, job.machine.port) not in l_hosts_ports:
                l_hosts_ports.append((job.machine.host, job.machine.port))
                
            distrib = job.machine.distribution
            application = job.application
            
            board_job = job.board
            if board is None:
                continue
            for board in self.d_xml_board_files:
                if board_job == board:
                    if (distrib not in [None, ''] and 
                                            distrib not in d_dist[board]):
                        d_dist[board].append(distrib)
                        ASNODE( self.d_xml_board_files[board].xmlroot.find('distributions'),
                                "dist",  attrib={"name" : distrib} )
                    
                if board_job == board:
                    if (application not in [None, ''] and 
                                    application not in d_application[board]):
                        d_application[board].append(application)
                        ASNODE( self.d_xml_board_files[board].xmlroot.find('applications'),
                                "application", attrib={"name" : application} )
        
        # Verify that there are no missing application or distribution in the
        # xml board files (regarding the input boards)
        for board in self.d_xml_board_files:
            l_dist = d_dist[board]
            if board not in self.d_input_boards.keys():
                continue
            for dist in self.d_input_boards[board]["rows"]:
                if dist not in l_dist:
                    ASNODE( self.d_xml_board_files[board].xmlroot.find('distributions'),
                            "dist", attrib={"name" : dist} )
            l_appli = d_application[board]
            for appli in self.d_input_boards[board]["columns"]:
                if appli not in l_appli:
                    ASNODE( self.d_xml_board_files[board].xmlroot.find('applications'),
                            "application", attrib={"name" : appli} )
                
        # Initialize the hosts_ports node for the global file
        self.xmlhosts_ports = self.xml_global_file.add_simple_node_root("hosts_ports")
        for host, port in l_hosts_ports:
            host_port = "%s:%i" % (host, port)
            ASNODE(self.xmlhosts_ports, "host_port", attrib={"name" : host_port})
        
        # Initialize the jobs node in all files
        for xml_file in [self.xml_global_file] + list(self.d_xml_board_files.values()):
            xml_jobs = xml_file.add_simple_node_root("jobs")      
            # Get the jobs present in the config file but 
            # that will not be launched today
            self.put_jobs_not_today(l_jobs_not_today, xml_jobs)
            
            # add also the infos node
            xml_file.add_simple_node_root( 
                "infos", attrib={"name" : "last update", "JobsCommandStatus" : "running"} )
            
            # and put the history node
            history_node = xml_file.add_simple_node_root("history")
            name_board = os.path.basename(xml_file.logFile)[:-len(".xml")]
            # serach for board files
            expression = "^[0-9]{8}_+[0-9]{6}_" + name_board + ".xml$"
            oExpr = re.compile(expression)
            # Get the list of xml borad files that are in the log directory
            for file_name in os.listdir(self.xml_dir_path):
                if oExpr.search(file_name):
                    date = os.path.basename(file_name).split("_")[0]
                    file_path = os.path.join(self.xml_dir_path, file_name)
                    ASNODE(history_node, "link", text=file_path, attrib={"date" : date})      
            
                
        # Find in each board the squares that needs to be filled regarding the
        # input csv files but that are not covered by a today job
        for board in self.d_input_boards.keys():
            xml_root_board = self.d_xml_board_files[board].xmlroot
            # Find the missing jobs for today
            xml_missing = ASNODE(xml_root_board, "missing_jobs")
            for row, column in self.d_input_boards[board]["jobs"]:
                found = False
                for job in l_jobs:
                    if (job.application == column and 
                        job.machine.distribution == row):
                        found = True
                        break
                if not found:
                    ASNODE(xml_missing, "job", attrib={"distribution" : row, "application" : column })
            # Find the missing jobs not today
            xml_missing_not_today = ASNODE( xml_root_board, "missing_jobs_not_today")
            for row, column in self.d_input_boards[board]["jobs_not_today"]:
                found = False
                for job in l_jobs_not_today:
                    if (job.application == column and 
                        job.machine.distribution == row):
                        found = True
                        break
                if not found:
                    ASNODE( xml_missing_not_today, "job",
                            attrib={"distribution" : row, "application" : column } )

    def find_history(self, l_jobs, l_jobs_not_today):
        """
        find, for each job, in the existent xml boards the results for the job.
        Store the results in the dictionary 
        self.history = {name_job : list of (date, status, list links)}
        
        :param l_jobs: (list) 
          the list of jobs to run today   
        :param l_jobs_not_today: (list) 
          the list of jobs that do not run today
        """
        # load the all the history
        expression = "^[0-9]{8}_+[0-9]{6}_" + self.global_name + ".xml$"
        oExpr = re.compile(expression)
        # Get the list of global xml that are in the log directory
        l_globalxml = []
        for file_name in os.listdir(self.xml_dir_path):
            if oExpr.search(file_name):
                file_path = os.path.join(self.xml_dir_path, file_name)
                try:
                    global_xml = XMLMGR.ReadXmlFile(file_path)
                    l_globalxml.append(global_xml)
                except Exception as e:
                    msg = _("The file '%s' can not be read, it will be ignored\n%s") % \
                           (file_path, e)
                    self.logger.warning("%s\n" % msg)
                    
        # Construct the dictionnary self.history 
        for job in l_jobs + l_jobs_not_today:
            l_links = []
            for global_xml in l_globalxml:
                date = os.path.basename(global_xml.filePath).split("_")[0]
                global_root_node = global_xml.xmlroot.find("jobs")
                job_node = XMLMGR.find_node_by_attrib(
                  global_root_node, "job", "name", job.name )
                if job_node:
                    if job_node.find("remote_log_file_path") is not None:
                        link = job_node.find("remote_log_file_path").text
                        res_job = job_node.find("res").text
                        if link != "nothing":
                            l_links.append((date, res_job, link))
            l_links = sorted(l_links, reverse=True)
            self.history[job.name] = l_links
  
    def put_jobs_not_today(self, l_jobs_not_today, xml_node_jobs):
        """
        Get all the first information needed for each file and write the 
        first version of the files   

        :param xml_node_jobs: (ETREE.Element) 
          the node corresponding to a job
        :param l_jobs_not_today: (list) 
          the list of jobs that do not run today
        """
        
        ASNODE = XMLMGR.add_simple_node # shortcut
        
        for job in l_jobs_not_today:
            xmlj = ASNODE(xml_node_jobs, "job", attrib={"name" : job.name})
            ASNODE(xmlj, "application", job.application)
            ASNODE(xmlj, "distribution", job.machine.distribution)
            ASNODE(xmlj, "board", job.board)
            ASNODE(xmlj, "commands", " ; ".join(job.commands))
            ASNODE(xmlj, "state", "Not today")
            ASNODE(xmlj, "machine", job.machine.name)
            ASNODE(xmlj, "host", job.machine.host)
            ASNODE(xmlj, "port", str(job.machine.port))
            ASNODE(xmlj, "user", job.machine.user)
            ASNODE(xmlj, "sat_path", job.machine.sat_path)
            xml_history = ASNODE(xmlj, "history")
            for i, (date, res_job, link) in enumerate(self.history[job.name]):
                if i==0:
                    # tag the first one (the last one)
                    ASNODE( xml_history, "link", text=link,
                            attrib={"date" : date, "res" : res_job, "last" : "yes"} )
                else:
                    ASNODE( xml_history, "link", text=link,
                            attrib={"date" : date, "res" : res_job, "last" : "no"} )

    def parse_csv_boards(self, today):
        """ 
        Parse the csv file that describes the boards to produce and fill 
        the dict d_input_boards that contain the csv file contain
        
        :param today: (int) the current day of the week 
        """
        # open the csv file and read its content
        l_read = []
        with open(self.file_boards, 'r') as f:
            reader = csv.reader(f,delimiter=CSV_DELIMITER)
            for row in reader:
                l_read.append(row)
        # get the delimiter for the boards (empty line)
        boards_delimiter = [''] * len(l_read[0])
        # Make the list of boards, by splitting with the delimiter
        l_boards = [list(y) for x, y in itertools.groupby(l_read,
                                    lambda z: z == boards_delimiter) if not x]
           
        # loop over the csv lists of lines and get the rows, columns and jobs
        d_boards = {}
        for input_board in l_boards:
            # get board name
            board_name = input_board[0][0]
            
            # Get columns list
            columns = input_board[0][1:]
            
            rows = []
            jobs = []
            jobs_not_today = []
            for line in input_board[1:]:
                row = line[0]
                rows.append(row)
                for i, square in enumerate(line[1:]):
                    if square=='':
                        continue
                    days = square.split(DAYS_SEPARATOR)
                    days = [int(day) for day in days]
                    job = (row, columns[i])
                    if today in days:                           
                        jobs.append(job)
                    else:
                        jobs_not_today.append(job)

            d_boards[board_name] = {"rows" : rows,
                                    "columns" : columns,
                                    "jobs" : jobs,
                                    "jobs_not_today" : jobs_not_today}
        
        self.d_input_boards = d_boards

    def update_xml_files(self, l_jobs):
        """Write all the xml files with updated information about the jobs   

        :param l_jobs: (list) the list of jobs that run today
        """
        for xml_file in [self.xml_global_file] + list(
                                            self.d_xml_board_files.values()):
            self.update_xml_file(l_jobs, xml_file)
            
        # Write the file
        self.write_xml_files()
            
    def update_xml_file(self, l_jobs, xml_file):      
        """update information about the jobs for the file xml_file   

        :param l_jobs: (list) the list of jobs that run today
        :param xml_file: (xmlManager.XmlLogFile) 
          the xml instance to update
        """
        
        xml_node_jobs = xml_file.xmlroot.find('jobs')
        # Update the job names and status node
        for job in l_jobs:
            # Find the node corresponding to the job and delete it
            # in order to recreate it
            for xmljob in xml_node_jobs.findall('job'):
                if xmljob.attrib['name'] == job.name:
                    xml_node_jobs.remove(xmljob)
            
            T0 = job._T0.toStrHuman()
            Tf = job._Tf.toStrHuman()
            
            # recreate the job node
            xmlj = ASNODE(xml_node_jobs, "job", attrib={"name" : job.name})
            ASNODE(xmlj, "machine", job.machine.name)
            ASNODE(xmlj, "host", job.machine.host)
            ASNODE(xmlj, "port", str(job.machine.port))
            ASNODE(xmlj, "user", job.machine.user)
            xml_history = ASNODE(xmlj, "history")
            for date, res_job, link in self.history[job.name]:
                ASNODE( xml_history, "link", text=link,
                        attrib={"date" : date, "res" : res_job} )

            ASNODE(xmlj, "sat_path", job.machine.sat_path)
            ASNODE(xmlj, "application", job.application)
            ASNODE(xmlj, "distribution", job.machine.distribution)
            ASNODE(xmlj, "board", job.board)
            ASNODE(xmlj, "timeout", str(job.timeout))
            ASNODE(xmlj, "commands", " ; ".join(job.commands))
            ASNODE(xmlj, "state", job.get_status())
            ASNODE(xmlj, "begin", T0)
            ASNODE(xmlj, "end", Tf)
            ASNODE(xmlj, "out", UTS.cleancolor(job.out))
            ASNODE(xmlj, "err", UTS.cleancolor(job.err))
            ASNODE(xmlj, "res", str(job.res_job))
            if len(job.remote_log_files) > 0:
                ASNODE(xmlj, "remote_log_file_path", job.remote_log_files[0])
            else:
                ASNODE(xmlj, "remote_log_file_path", "nothing")           
            # Search for the test log if there is any
            l_test_log_files = self.find_test_log(job.remote_log_files)
            xml_test = ASNODE(xmlj, "test_log_file_path")
            for test_log_path, res_test, nb_fails in l_test_log_files:
                test_path_node = ASNODE(xml_test, "path", test_log_path)
                test_path_node.attrib["res"] = res_test
                test_path_node.attrib["nb_fails"] = nb_fails
            
            xmlafter = ASNODE(xmlj, "after", job.after)
            # get the job father
            if job.after is not None:
                job_father = None
                for jb in l_jobs:
                    if jb.name == job.after:
                        job_father = jb
                
                if (job_father is not None and 
                        len(job_father.remote_log_files) > 0):
                    link = job_father.remote_log_files[0]
                else:
                    link = "nothing"
                XMLMGR.append_node_attrib(xmlafter, {"link" : link})
            
            # Verify that the job is to be done today regarding the input csv
            # files
            if job.board and job.board in self.d_input_boards.keys():
                found = False
                for dist, appli in self.d_input_boards[job.board]["jobs"]:
                    if (job.machine.distribution == dist 
                        and job.application == appli):
                        found = True
                        ASNODE(xmlj, "extra_job", "no")
                        break
                if not found:
                    ASNODE(xmlj, "extra_job", "yes")
            
        
        # Update the date
        xml_node_infos = xml_file.xmlroot.find('infos')
        XMLMGR.append_node_attrib( xml_node_infos,
           attrib={"value" : DATT.DateTime("now").toStrHuman()} )
               

    def find_test_log(self, l_remote_log_files):
        """
        Find if there is a test log (board) in the remote log files and 
        the path to it. There can be several test command, 
        so the result is a list.

        :param l_remote_log_files: (list) the list of all remote log files
        :return: (list) 
          the list of tuples (test log files path, res of the command)
        """
        res = []
        for file_path in l_remote_log_files:
            dirname = os.path.basename(os.path.dirname(file_path))
            file_name = os.path.basename(file_path)
            regex = UTS._log_all_command_file_expression
            oExpr = re.compile(regex)
            if dirname == "TEST" and oExpr.search(file_name):
                # find the res of the command
                prod_node = ETREE.parse(file_path).getroot().find("product")
                res_test = prod_node.attrib["global_res"]
                # find the number of fails
                testbase_node = prod_node.find("tests").find("testbase")
                nb_fails = int(testbase_node.attrib["failed"])
                # put the file path, the res of the test command and the number 
                # of fails in the output
                res.append((file_path, res_test, nb_fails))
                
        return res
    
    def last_update(self, finish_status = "finished"):
        """update information about the jobs for the file xml_file   

        :param l_jobs: (list) the list of jobs that run today
        :param xml_file: (xmlManager.XmlLogFile) the xml instance to update
        """
        for xml_file in [self.xml_global_file] + list(self.d_xml_board_files.values()):
            xml_node_infos = xml_file.xmlroot.find('infos')
            XMLMGR.append_node_attrib(xml_node_infos,
                        attrib={"JobsCommandStatus" : finish_status})
        # Write the file
        self.write_xml_files()

    def write_xml_file(self, xml_file, stylesheet):
        """
        Write one xml file and the same file with prefix
        """
        xml_file.write_tree(stylesheet)
        file_path = xml_file.logFile
        file_dir = os.path.dirname(file_path)
        file_name = os.path.basename(file_path)
        file_name_with_prefix = self.prefix + "_" + file_name
        xml_file.write_tree(stylesheet, os.path.join(file_dir,
                                                     file_name_with_prefix))
        
    def write_xml_files(self):
        """
        Write the xml files   
        """
        self.write_xml_file(self.xml_global_file, STYLESHEET_GLOBAL)
        for xml_file in self.d_xml_board_files.values():
            self.write_xml_file(xml_file, STYLESHEET_BOARD)

def get_config_file_path(job_config_name, l_cfg_dir):
    found = False
    file_configs_jobs = None
    if os.path.exists(job_config_name) and job_config_name.endswith(".pyconf"):
        found = True
        file_configs_jobs = job_config_name
    else:
        for cfg_dir in l_cfg_dir:
            file_configs_jobs = os.path.join(cfg_dir, job_config_name)
            if not file_configs_jobs.endswith('.pyconf'):
                file_configs_jobs += '.pyconf'
            
            if not os.path.exists(file_configs_jobs):
                continue
            else:
                found = True
                break
    return found, file_configs_jobs

def develop_factorized_jobs(config_jobs):
    """update information about the jobs for the file xml_file   
    
    :param config_jobs: (Config) 
      the config corresponding to the jos description
    """
    developed_jobs_list = []
    for jb in config_jobs.jobs:
        # case where the jobs are not developed
        if type(jb.machine) == type(""):
            developed_jobs_list.append(jb)
            continue
        # Case where the jobs must be developed
        # Example:
        # machine : ["CO7.2 physique", ["CO6.4 physique", $MONDAY, $TUESDAY ], "FD22"]
        name_job = jb.name
        for machine in jb.machine:
            new_job = PYCONF.deepCopyMapping(jb)
            # case where there is a jobs on the machine corresponding to all
            # days in when variable. 
            if type(machine) == type(""):
                new_job.machine = machine
                new_job.name = name_job + " / " + machine
            else:
                # case the days are re defined
                new_job.machine = machine[0]
                new_job.name = name_job + " / " + machine[0]
                new_job.when = machine[1:]
            developed_jobs_list.append(new_job)
    
    config_jobs.jobs = developed_jobs_list
            
