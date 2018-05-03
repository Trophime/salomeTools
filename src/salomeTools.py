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
This file is the main entry file to salomeTools
NO __main__ entry allowed, use 'sat' (in parent directory)
"""

########################################################################
# NO __main__ entry allowed, use sat
########################################################################
if __name__ == "__main__":
    sys.stderr.write("\nERROR: 'salomeTools.py' is not main command entry for sat: use 'sat' instead.\n\n")
    KOSYS = 1 # avoid import src
    sys.exit(KOSYS)

import os
import sys
import re
import tempfile
import imp
import gettext
import traceback
import subprocess as SP
import pprint as PP

import src # for __version__
import src.debug as DBG # Easy print stderr (for DEBUG only)
import src.returnCode as RCO # Easy (ok/ko, why) return methods code
from src.options import Options
import configManager as CFGMGR

# get path to src
rootdir = os.path.realpath( os.path.join(os.path.dirname(__file__), "..") )
DBG.write("sat rootdir", rootdir)  
srcdir = os.path.join(rootdir, "src")
cmdsdir = os.path.join(rootdir, "commands")

# load resources for internationalization
gettext.install("salomeTools", os.path.join(srcdir, "i18n"))

# The possible hooks : 
# pre is for hooks to be executed before commands
# post is for hooks to be executed after commands
C_PRE_HOOK = "pre"
C_POST_HOOK = "post"

_LANG = os.environ["LANG"] # original locale

########################################################################
# utility methods
########################################################################
def find_command_list(dirPath):
    """
    Parse files in dirPath that end with '.py' : it gives commands list
    
    :param dirPath: (str) The directory path where to search the commands
    :return: (list) the list containing the commands name 
    """
    cmd_list = []
    for item in os.listdir(dirPath):
        if item in ["__init__.py"]: #avoid theses files
            continue
        if item.endswith(".py"):
            cmd_list.append(item[:-len(".py")])
    return sorted(cmd_list)

# The list of valid salomeTools commands from cmdsdir
# ['config', 'compile', 'prepare', ...]
_COMMANDS_NAMES = find_command_list(cmdsdir)

def getCommandsList():
    """Gives commands list (as basename of files .py in directory commands""" 
    return _COMMANDS_NAMES

def launchSat(command):
    """
    launch sat as subprocess.Popen
    command as string ('sat --help' for example)
    used for unittest, or else...
    
    :return: (stdout, stderr) tuple of subprocess.Popen output
    """
    if "sat" not in command.split()[0]:
      raise Exception(_("Not a valid command for launchSat: '%s'") % command)
    env = dict(os.environ) # copy
    # theorically useless, in user environ $PATH,
    # on ne sait jamais
    # https://docs.python.org/2/library/os.html
    # On some platforms, including FreeBSD and Mac OS X, 
    # setting environ may cause memory leaks.
    # see test/initializeTest.py
    if rootdir not in env["PATH"].split(":"):
      env["PATH"] = rootdir + ":" + env["PATH"]
    # TODO setLocale not 'fr' on subprocesses, why not?
    # env["LANG"] == ''
    res = SP.Popen(command, shell=True, env=env, stdout=SP.PIPE, stderr=SP.PIPE).communicate()
    return res

def setNotLocale():
    """force english at any moment"""
    os.environ["LANG"] = ''
    gettext.install("salomeTools", os.path.join(srcdir, "i18n"))
    DBG.write("setNotLocale", os.environ["LANG"])
    
def setLocale():
    """\
    reset initial locale at any moment 
    'fr' or else (TODO) from initial environment var '$LANG'
    'i18n' as 'internationalization'
    """
    os.environ["LANG"] = _LANG
    gettext.install("salomeTools", os.path.join(srcdir, "i18n"))
    DBG.write("setLocale", os.environ["LANG"])
    
def getVersion():
    """get version number as string"""
    return src.__version__
 
def assumeAsList(strOrList):
    """return a list as sys.argv if string"""
    if type(strOrList) is list:
      return list(strOrList) # copy
    else:
      res = strOrList.split(" ")
      return [r for r in res if r != ""] # supposed string to split for convenience

########################################################################
# _BaseCmd class
########################################################################
class _BaseCommand(object):
    """
    _BaseCmd is the base class for all inherited commands of salomeTools
    instancied as classes 'Command' in files '.../commands/*.py'
    """
  
    # supposed never seen, set "config", "prepare"... in inherited commands
    name = "salomeTools"
    
    def __init__(self, runner):
        # runner (as caller) usually as Sat instance
        self._runner = runner
        # config pyconf usually loaded in runner, but sometimes local value
        self._config = None
        # logger (from caller) usually as Sat instance logger, but sometimes local value
        self._logger = runner.logger
        self._options = None
        
    def getClassName(self):
        """
        returns 'config.Command' or prepare.Command' for example 
        as inherited classes 'Command' in files
        '.../commands/config.py' or '.../commands/prepare.py'
        """
        return "%s.%s" % (self.name, self.__class__.__name__)

    def __repr__(self):
        tmp = PP.pformat(self.__dict__)
        res = "%s(\n %s)\n" % (self.getClassName(), tmp[1:-1])
        return res

    def run(self, cmd_arguments):
        """
        virtual example method for Command instance
        have to return RCO.ReturnCode()
        """
        return RCO.ReturnCode("KO", "_BaseCommand.run() have not to be instancied and called")
           
    def setLogger(self, logger):
        """set logger for run command"""
        if self._logger is not None:
          # supposed logger.debug for future
          self._logger.warning("change logger for %s, are you sure" % self.getClassName())
        self._logger = logger
            
    def getLogger(self):
        if self._logger is None:
          raise Exception("%s instance needs self._logger not None, fix it." % self.getClassName())
        else:
          return self._logger

    def getOptions(self):
        if self._options is None:
          raise Exception("%s instance needs self._option not None, fix it." % self.getClassName())
        else:
          return self._options
    
    def getParserWithHelp(self):
        """returns elementary parser with help option set"""
        parser = Options()
        parser.add_option('h', 'help', 'boolean', 'help', _("shows help on command."))
        return parser

    def getRunner(self):
        if self._runner is None:
          raise Exception("%s instance needs self.runner not None, fix it." % self.getClassName())
        else:
          return self._runner

    def getConfig(self):
        """
        supposedly (for now) no multiply local config(s)
        only one config in runner.config
        may be some for future...
        """
        if self._runner.config is None:
          self._logger.error("%s instance have runner.config None, fix it." % self.getClassName())
        return self._runner.config

    def assumeAsList(self, strOrList):
        return assumeAsList(strOrList)
                  
    def getParser(self):
        raise Exception("_BaseCmd class have not to be instancied, only for inheritage")

    def parseArguments(self, cmd_arguments):
        """
        smart parse command arguments skip
        first argument name appli to load, if present
        """
        argList = self.assumeAsList(cmd_arguments)
        DBG.write("%s.Command arguments" % self.name, argList)
        commandOptions, remaindersArgs = self.getParser().parse_args(argList)
        DBG.write("%s.Command options" % self.name, commandOptions)
        DBG.write("%s.Command remainders arguments" % self.name, remaindersArgs)
        if remaindersArgs != []:
          self.getLogger().error("%s.Command have unknown remainders arguments:\n%s\n" % \
                                 (self.name, remaindersArgs))
        return commandOptions, remaindersArgs
    
    def description(self):
        """
        method called when salomeTools have '--help' argument.
        returns The text to display for the command description
        which is current Command class docstring 'self.__doc__',
        with traduction, if done.
        replace supposedly sphinx apidoc format ' | ' if present
        """
        return _(self.__doc__.replace(" | ", " ")) # replace sphinx apidoc format
    
    def run(self, cmd_arguments):
        """
        method called when salomeTools processes command(s) parameters
        """
        raise Exception("_BaseCmd class have not to be instancied, useful only for inheritage")

    def print_help(self):
        """
        Prints help for a command. Function called with 
        'sat --help <command>' or
        'sat --help <command> --help' or
        'sat <command>' without any trailing arguments
        """
        msg = self.get_help()
        self._logger.info(msg)
            
    def get_help(self):
        """get string help for inherited Command classes"""
        version = getVersion() + "\n\n" # salomeTools version
        msg = "<header>Version:<reset> " + version
        # description of the command that is done in the command.py file
        msg += "<header>Description:<reset>\n"
        msg += self.description() + "\n\n"
        
        # description of the command options
        msg += self.getParser().get_help() + "\n"
        return msg

########################################################################
# Sat class
########################################################################
class Sat(object):
    """
    The main class that stores all the commands of salomeTools
    (usually known as 'runner' argument in Command classes)
    """
    def __init__(self, logger):
        """Initialization
        
        :param logger: (Logger) The logger to use
        """

        # Read the salomeTools prefixes options before the 'commands' tag
        # sat <options> <args>
        # (the list of possible options is at the beginning of this file)
        
        self.configManager = None # the config Manager that will be used to set self.config
        self.config = None # the config that will be read using pyconf module
        self.logger = logger # the logger that will be use
        self.arguments = None # args are postfixes options: args[0] is the 'commands' command
        self.options = None # the options passed to salomeTools
        
        # the directory that contain all the external 
        # data (like software pyconf and software scripts)
        self.datadir = None # default value will be <salomeTools root>/data
        
        # contains commands classes needed (think micro commands)
        # if useful 'a la demande'
        self.commands = {}
        self.nameCommandToLoad = None
        self.nameAppliToLoad = None
        self.commandArguments = None
        self.nameAppliLoaded = None
      
        self.parser = self._getParser()
                
    def __repr__(self):
        aDict = {
          "arguments": self.arguments, 
          "options": self.options,
          "datadir": self.datadir,
          "commands": sorted(self.commands.keys()),
        }
        tmp = PP.pformat(aDict)
        res = "Sat(\n %s\n)\n" % tmp[1:-1]
        return res
    
    def getLogger(self):
        if self.logger is None: # could use owner Sat instance logger
          import src.loggingSat as LOG
          self.logger=LOG.getDefaultLogger()
          self.logger.critical("Sat logger not set, unexpected situation, fixed as default")
          return self.logger
        else:                   # could use local logger
          return self.logger
        
    def getConfig(self):
        return self.config
        
    def assumeAsList(self, strOrList):
        return assumeAsList(strOrList)

    def _getParser(self):
        """
        Define all possible <options> for salomeTools/sat command: 'sat <options> <args>'
        (internal use only)
        """
        parser = Options()
        parser.add_option('h', 'help', 'boolean', 'help', 
                          _("shows global help or help on a specific command."))
        parser.add_option('o', 'overwrite', 'list', "overwrite", 
                          _("overwrites a configuration parameters."))
        parser.add_option('g', 'debug', 'boolean', 'debug_mode', 
                          _("run salomeTools in debug mode."))
        parser.add_option('v', 'verbose', 'int', "output_verbose_level", 
                          _("change output verbose level (default is 3)."))
        parser.add_option('b', 'batch', 'boolean', "batch", 
                          _("batch mode (no question)."))
        parser.add_option('t', 'all_in_terminal', 'boolean', "all_in_terminal", 
                          _("all traces in the terminal (for example compilation logs)."))
        parser.add_option('l', 'logs_paths_in_file', 'string', "logs_paths_in_file", 
                          _("put the command result and paths to log files."))
        return parser
 
     
    def parseArguments(self, arguments):
        args = self.assumeAsList(arguments)
        genericOptions, remaindersArgs = self.parser.parse_args(args)
        DBG.write("Sat generic options", genericOptions)
        DBG.write("Sat remainders arguments", remaindersArgs)
        return genericOptions, remaindersArgs
               
    
    def _getModule(self, name):
        """
        load and add module Command 'name' in dict self.commands
        have to be called only one time maximum for each module Command
        """
        if name not in _COMMANDS_NAMES:
            raise Exception(_("module command not valid: '%s'") % name)
        if name in self.commands.keys():
            raise Exception(_("module command existing yet: '%s', use getModule") % name)
        file_, pathname, description = imp.find_module(name, [cmdsdir])
        # could raise Exception in load (catched in sat, logger.critical)
        module = imp.load_module(name, file_, pathname, description)
        self.commands[name] = module # store module loaded (only one time)
        self.logger.debug("Sat load module command %s" % name)
        return module
      
    def getModule(self, name):
        """
        returns only-one-time loaded module Command 'name'
        assume load if not done yet
        """
        if name in self.commands.keys():
          return self.commands[name]
        else:
          return self._getModule(name)
        
    def getCommandInstance(self, name):
        """
        returns inherited instance of Command(_BaseCmd) for command 'name'
        if module not loaded yet, load it.
        """
        module = self.getModule(name)
        try:
          commandInstance = module.Command(self)  # set runner as 'parent' (and logger...)
        except Exception as e:
          raise Exception("Problem instance %s.Command(): %s" % (name, e))
        self.logger.debug("Sat new instance %s.Command()" % name)
        return commandInstance                          

    def execute_cli(self, cli_arguments):
        """select first argument as a command in directory 'commands', and launch on arguments
        
        :param cli_arguments: (str or list) The sat cli arguments (as sys.argv)
        """
        args = self.assumeAsList(cli_arguments)

        # print general help and returns
        if len(args) == 0:
            self.print_help()
            return RCO.ReturnCode("OK", "No arguments, as 'sat --help'")
        
        self.options, remainderArgs = self.parseArguments(args)
        
        # if the help option has been called, print command help and returns
        if self.options.help:
            self.print_help()
            return RCO.ReturnCode("OK", "Option --help")
       
        self.nameCommandToLoad, self.nameAppliToLoad, self.commandArguments = \
             self.getCommandAndAppli(remainderArgs)
             
        cfgManager = CFGMGR.ConfigManager(self)
        self.config = cfgManager.get_config(
                        application=self.nameAppliToLoad,
                        options=self.options,
                        command=self.nameCommandToLoad,
                        datadir=None)
        
        # create/get dynamically the command instance to call its 'run' method
        cmdInstance = self.getCommandInstance(self.nameCommandToLoad)
        
        # Run the command using the arguments
        returnCode = cmdInstance.run(self.commandArguments)
        return returnCode
        
    def getCommandAndAppli(self, arguments):
        args = self.assumeAsList(arguments)
        namecmd, nameAppli, remainderArgs = None, None, []
        iremain = 0
        if len(args) > 0:
          if "-" != args[0][0]: 
            namecmd = args[0]
            iremain = 1
        if len(args) > 1:
          if "-" != args[1][0]: 
            nameAppli = args[1]
            iremain = 2
        remainderArgs = args[iremain:]
        res = (namecmd, nameAppli, remainderArgs)
        DBG.write("getCommandAndAppli", res)
        return res
        
      
    def get_help(self):
        """get general help colored string"""
        msg = self.getColoredVersion() + "\n\n"
        msg += "<header>Usage:<reset>  sat [generic_options] <command> [product] [command_options]\n\n"
        msg += self._getParser().get_help() + "\n"
        msg += "<header>" + _("Available commands are:") + "<reset>\n\n"
        for command in _COMMANDS_NAMES:
            msg += " - %s\n" % (command)
        msg += "\n"
        # how to get the help for a specific command
        msg += "<header>" + _("Getting the help for a specific command: ") + \
               "<reset>sat <command> --help\n"
        return msg
    
    def print_help(self):
        """prints salomeTools general help"""
        self.logger.info(self.get_help())
          
    def getConfigManager(self):
        import src.configManager as CFGMGR
        return CFGMGR.ConfigManager(self.logger)
        
    def getColoredVersion(self):
        """get colored salomeTools version message"""
        version = getVersion()
        if self.config is not None:
          # verify coherency with config.INTERNAL.sat_version
          if config.INTERNAL.sat_version != version:
            self.logger.warning("verify version with INTERNAL.sat_version")
        msg = "<header>Version:<reset> " + version
        return msg
   
       



