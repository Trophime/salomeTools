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

'''This file is the main entry file to salomeTools
'''

import os
import sys
import re
import tempfile
import imp
import gettext
import traceback
import subprocess as SP
import pprint as PP


########################################################################
# NOT MAIN entry allowed, use sat
########################################################################
if __name__ == "__main__":
    sys.stderr.write("\nERROR: 'salomeTools.py' is not main command entry for sat: use 'sat' instead.\n\n")
    KOSYS = 1 # avoid import src
    sys.exit(KOSYS)


import src.debug as DBG # Easy print stderr (for DEBUG only)
import src.returnCode as RCO # Easy (ok/ko, why) return methods code
import src

# get path to src
rootdir = os.path.realpath( os.path.join(os.path.dirname(__file__), "..") )
DBG.write("sat rootdir", rootdir)  
srcdir = os.path.join(rootdir, "src")
cmdsdir = os.path.join(rootdir, "commands")

# load resources for internationalization
gettext.install('salomeTools', os.path.join(srcdir, 'i18n'))

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
    '''Parse files in dirPath that end with .py : it gives commands list
    
    :param dirPath str: The directory path where to search the commands
    :return: cmd_list : the list containing the commands name 
    :rtype: list
    '''
    cmd_list = []
    for item in os.listdir(dirPath):
        if item in ["__init__.py"]: #avoid theses files
            continue
        if item.endswith('.py'):
            cmd_list.append(item[:-len('.py')])
    return cmd_list

# The list of valid salomeTools commands from cmdsdir
#_COMMANDS_NAMES = ['config', 'compile', 'prepare',...]
_COMMANDS_NAMES = find_command_list(cmdsdir)

def getCommandsList():
    """Gives commands list (as basename of files cmdsdir/*.py)
    """ 
    return _COMMANDS_NAMES

def launchSat(command):
    """launch sat as subprocess popen
    command as string ('sat --help' for example)
    used for unittest, or else...
    returns tuple (stdout, stderr)
    """
    if "sat" not in command.split()[0]:
      raise Exception(_("Not a valid command for launchSat: '%s'") % command)
    env = dict(os.environ)
    env["PATH"] = rootdir + ":" + env["PATH"]
    res =SP.Popen(command, shell=True, env=env, stdout=SP.PIPE, stderr=SP.PIPE).communicate()
    return res

def setNotLocale():
    """force english at any moment"""
    os.environ["LANG"] = ''
    gettext.install('salomeTools', os.path.join(srcdir, 'i18n'))
    DBG.write("setNotLocale", os.environ["LANG"])
    
def setLocale():
    """reset initial locale at any moment 
    'fr' or else 'TODO' from initial environment var '$LANG'
    """
    os.environ["LANG"] = _LANG
    gettext.install('salomeTools', os.path.join(srcdir, 'i18n'))
    DBG.write("setLocale", os.environ["LANG"])
    

########################################################################
# _BaseCmd class
########################################################################
class _BaseCommand(object):
    '''_BaseCmd is the base class for all inherited commands of salomeTools
    instancied as classes 'Command' in files '.../commands/*.py'
    '''
    def __init__(self, name):
        self.name = name
        self.runner = None # runner (as caller) usually as Sat instance
        # self.config = None # config pyconf usually loaded with _getConfig method
        self.logger = None # logger (from caller) usually as Sat instance logger
        
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

    def run(self, args):
        return RCO.ReturnCode("KO", "_BaseCommand.run() have to be inherited")
    
    def setRunner(self, runner):
        """set who owns me, and use me whith method run()"""
        self.runner  = runner
        
    def setLogger(self, logger):
        """set logger for run command"""
        self.logger = logger
        
    def getLogger(self):
        if self.logger is None: # could use runner Sat instance logger
          return self.runner.getLogger()
        else:                   # could use local logger
          return self.logger
        
    def getRunner(self):
        if self.runner is None:
          raise Exception("have to set runner attribute, fix it.")
        else:
          return self.runner
                  
    def getParser(self):
        raise Exception("_BaseCmd class have not to be instancied, only for inheritage")

    def parse_args(self, args):
        """smart parse command arguments skipping first argument name appli to load if present"""
        parser = self.getParser()
        if type(args) is list:
          argList = args
        else:
          argList = args.split(' ')
        DBG.write("%s args" % self.name, args, True)
        # or if args[0][0] == "-": #as argument name appli without "--"
        if self.runner.nameAppliLoaded is None:
          (options, argsc) = parser.parse_args(args)
        else:
          (options, argsc) = parser.parse_args(args[1:]) # skip name appli
        DBG.write("%s options" % self.name, options)
        DBG.write("%s remainders args" % self.name, argsc)
        if argsc != []:
          self.getLogger().error("\n\ncommand '%s' remainders args %s\n\n" % (self.name, argsc))
        return (options, argsc)
    
    def description(self):
        '''method that is called when salomeTools is called with --help option.
        
        :return: The text to display for the config command description.
        :rtype: str
        '''
        raise Exception("_BaseCmd class have not to be instancied, only for inheritage")
    
    def run(self, args, runner, logger):
        '''method that is called when salomeTools is called with self.name parameter.
        '''
        raise Exception("_BaseCmd class have not to be instancied, only for inheritage")

    def getConfig(self):
        if self.runner.config is None:
          self.runner.config = self._getConfig()
        #DBG.write("_baseCommand runner", self.runner)
        DBG.write("_baseCommand runner.config", self.runner.config)
        return self.runner.config

    def _getConfig(self):
        '''The function that will load the configuration (all pyconf)
        and returns the config from files .pyconf
        '''
        if self.runner.config is not None:
          raise Exception("config existing yet in 's' instance" % self.runner.getClassName())
          
        # Get the arguments in a list and remove the empty elements
        # DBG.write("%s.runner.arguments" % self.name, self.runner.arguments)

        self.parser = self.getParser() 
        try:
            options, args = self.parser.parse_args(self.runner.arguments[1:])
            DBG.write("%s args" % self.name, args)
            DBG.write("%s options" % self.name, options)    
        except Exception as exc:
            write_exception(exc)
            sys.exit(RCO.KOSYS)

        self.arguments = args # args are postfixes options: args[0] is the 'commands' command
        self.options = options # the options passed to salomeTools
          
        if type(args) == type(''):
            # split by spaces without considering spaces in quotes
            argv_0 = re.findall(r'(?:"[^"]*"|[^\s"])+', args)
        else:
            argv_0 = args
        
        if argv_0 != ['']:
            while "" in argv_0: argv_0.remove("")
        
        # Format the argv list in order to prevent strings 
        # that contain a blank to be separated
        argv = []
        elem_old = ""
        for elem in argv_0:
            if argv == [] or elem_old.startswith("-") or elem.startswith("-"):
                argv.append(elem)
            else:
                argv[-1] += " " + elem
            elem_old = elem
                   
        # if it is provided by the command line, get the application
        appliToLoad = None
        if argv not in [[''], []] and argv[0][0] != "-":
            appliToLoad = argv[0].rstrip('*')
            argv = argv[1:]
        
        # Check if the global options of salomeTools have to be changed
        if options:
            options_save = self.options
            self.options = options  

        # read the configuration from all the pyconf files    
        cfgManager = getConfigManager() # commands.config.ConfigManager()
        DBG.write("appli to load", appliToLoad, True)
        config = cfgManager.get_config(datadir=self.runner.datadir, 
                                       application=appliToLoad, 
                                       options=self.runner.options, 
                                       command=self.name) # command=__nameCmd__)
        self.runner.nameAppliLoaded = appliToLoad
        # DBG.write("appli loaded", config, True)
                       
        # Set the verbose mode if called
        DBG.tofix("verbose/batch/logger_add_link -1/False/None", True)
        verbose = -1
        batch = False
        logger_add_link = None
        if verbose > -1:
            verbose_save = self.options.output_verbose_level
            self.options.__setattr__("output_verbose_level", verbose)    

        # Set batch mode if called
        if batch:
            batch_save = self.options.batch
            self.options.__setattr__("batch", True)

        # set output level
        if self.runner.options.output_verbose_level is not None:
            config.USER.output_verbose_level = self.runner.options.output_verbose_level
        if config.USER.output_verbose_level < 1:
            config.USER.output_verbose_level = 0
        silent = (config.USER.output_verbose_level == 0)

        # create log file
        micro_command = False
        if logger_add_link:
            micro_command = True
        logger_command = src.logger.Logger(config, 
                           silent_sysstd=silent,
                           all_in_terminal=self.runner.options.all_in_terminal,
                           micro_command=micro_command)
        
        # Check that the path given by the logs_paths_in_file option
        # is a file path that can be written
        if self.runner.options.logs_paths_in_file and not micro_command:
            try:
                self.options.logs_paths_in_file = os.path.abspath(
                                        self.options.logs_paths_in_file)
                dir_file = os.path.dirname(self.options.logs_paths_in_file)
                if not os.path.exists(dir_file):
                    os.makedirs(dir_file)
                if os.path.exists(self.options.logs_paths_in_file):
                    os.remove(self.options.logs_paths_in_file)
                file_test = open(self.options.logs_paths_in_file, "w")
                file_test.close()
            except Exception as e:
                msg = _("WARNING: the logs_paths_in_file option will "
                        "not be taken into account.\nHere is the error:")
                logger_command.write("%s\n%s\n\n" % (
                                     src.printcolors.printcWarning(msg),
                                     str(e)))
                self.options.logs_paths_in_file = None
                
        return config

    def get_products_list(self, options, cfg, logger):
        '''method that gives the product list with their informations from 
           configuration regarding the passed options.
        
        :param options Options: The Options instance that stores the commands 
                                arguments
        :param config Config: The global configuration
        :param logger Logger: The logger instance to use for the display and logging
        :return: The list of (product name, product_informations).
        :rtype: List
        '''
        # Get the products to be prepared, regarding the options
        if options.products is None:
            # No options, get all products sources
            products = cfg.APPLICATION.products
        else:
            # if option --products, check that all products of the command line
            # are present in the application.
            products = options.products
            for p in products:
                if p not in cfg.APPLICATION.products:
                    raise src.SatException(_("Product %(product)s "
                                "not defined in application %(application)s") %
                            { 'product': p, 'application': cfg.VARS.application} )
        
        # Construct the list of tuple containing 
        # the products name and their definition
        products_infos = src.product.get_products_infos(products, cfg)
        
        return products_infos


########################################################################
# Sat class
########################################################################
class Sat(object):
    '''The main class that stores all the commands of salomeTools
    '''
    def __init__(self, opt='', datadir=None):
        '''Initialization
        
        :param opt str or list: The sat options 
        :param: datadir str : the directory that contain all the external 
                              data (like software pyconf and software scripts)
        '''
        # Read the salomeTools prefixes options before the 'commands' tag
        # sat <options> <args>
        # (the list of possible options is  at the beginning of this file)
        
        # DBG.push_debug(True)

        self.parser = self._getParser() 
        try:
            if type(opt) is not list: # as string 'sat --help' for example'
                opts = opt.split()
            else:
                opts = opt
            options, args = self.parser.parse_args(opts)
            DBG.write("Sat options", options)
            DBG.write("Sat remainders args", args)
               
        except Exception as exc:
            write_exception(exc)
            sys.exit(RCO.KOSYS)

        self.config = None # the config that will be read using pyconf module
        self.logger = None # the logger that will be use
        self.arguments = args # args are postfixes options: args[0] is the 'commands' command
        self.options = options # the options passed to salomeTools
        self.datadir = datadir # default value will be <salomeTools root>/data
        # contains commands classes needed (think micro commands)
        # if useful 'a la demande'
        self.commands = {}
        self.nameAppliLoaded = None
        
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
          import src.logger as LOG
          self.logger=LOG.getDefaultLogger(self.config)
          return self.logger
        else:                   # could use local logger
          return self.logger


    def _getParser(self):
        """
        Define all possible <options> for salomeTools/sat command: 'sat <options> <args>'
        (internal use only)
        """
        import src.options
        parser = src.options.Options()
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


    def _getCommand(self, name):
        """
        create and add Command 'name' as instance of class in dict self.commands
        create only one instance
        """
        if name not in _COMMANDS_NAMES:
            raise AttributeError(_("command not valid: '%s'") % name)
        if name in self.commands.keys():
            raise AttributeError(_("command existing yet: '%s', use getCommand") % name)
        file_, pathname, description = imp.find_module(name, [cmdsdir])
        module = imp.load_module(name, file_, pathname, description)
        try:
          cmdInstance = module.Command(name)
        except:
          DBG.tofix("no Command() class in %s" % pathname, dir(module), True)
          raise Exception("no Command() class in %s" % pathname)

        cmdInstance.setRunner(self) # self is runner, owns cmdInstance
        DBG.write("Sat load new command", cmdInstance)
        return cmdInstance       
                    
    def getCommand(self, name):
        """
        returns inherited instance of _BaseCmd for command 'name'
        if not existing as self.commands[name], create it.
        
        example:
        returns Command() from command.config 
        """
        if name not in self.commands.keys():
            self.commands[name] = self._getCommand(name)
        return self.commands[name]    
       
    def execute_command(self, opt=None):
        """select first argument as a command in directory 'commands', and launch on arguments
        
        :param opt str, optionnal: The sat options (as sys.argv)
        """
        if opt is not None:
            args = opt
        else:
            args = self.arguments 

        # print general help and returns
        if len(args) == 0:
            print_help()
            return RCO.ReturnCode("OK", "No arguments as --help")
            
        # if the help option has been called, print command help and returns
        if self.options.help:
            self.print_help(self.arguments)
            return RCO.ReturnCode("OK", "Option --help")
       
        # the command called
        cmdName = args[0]
        # create/get dynamically the command instance to call its 'run' method
        cmdInstance = self.getCommand(cmdName)
        # Run the command using the arguments
        returnCode = cmdInstance.run(args[1:])
        return returnCode

    def print_help(self, opt):
        '''Prints help for a command. Function called when "sat -h <command>"
        
        :param argv str: the options passed (to get the command name)
        '''
        # if no command as argument (sat -h)
        if len(opt)==0:
            print_help()
            return
            
        # get command name
        cmdName = opt[0]
        # read the configuration from all the pyconf files
        cfgManager = getConfigManager()
        self.cfg = cfgManager.get_config(datadir=self.datadir)

        cmdInstance = self.getCommand(cmdName)
                   
        msg = self.get_command_help(cmdInstance)
            
        if isStdoutPipe():
            # clean color if the terminal is redirected by user
            # ex: sat compile appli > log.txt
            msg = src.printcolors.cleancolor(msg)  
        print(msg)
        return 
            
    def get_command_help(self, module):
        """get help for a command
        as 'sat --help config' for example
        """
        # get salomeTools version
        msg = get_version() + "\n\n"
        
        # print the description of the command that is done in the command file
        try:
            msg += src.printcolors.printcHeader( _("Description:") ) + "\n"
            msg += module.description() + "\n\n"
        except:
            DBG.tofix("no description() for", module.name, True)

        # print the description of the command options
        try:
            msg += module.getParser().get_help() + "\n"
        except:
            DBG.tofix("no getParser() for", module.name, True)
        return msg
      
        
###################################################################     
def getConfigManager():
    import commands.config 
    return commands.config.ConfigManager()
        
def get_text_from_options(options):
    text_options = ""
    for attr in dir(options):
        if attr.startswith("__"):
            continue
        if options.__getattr__(attr) != None:
            option_contain = options.__getattr__(attr)
            if type(option_contain)==type([]):
                option_contain = ",".join(option_contain)
            if type(option_contain)==type(True):
                option_contain = ""
            text_options+= "--%s %s " % (attr, option_contain)
    return text_options
         

def isStdoutPipe():
    """check if the terminal is redirected by user (elsewhere a tty) 
    example: 
    >> sat compile appli > log.txt
    """
    return not ('isatty' in dir(sys.stdout) and sys.stdout.isatty())
     
def get_version():
    """get version colored string
    """
    cfgManager = getConfigManager()
    cfg = cfgManager.get_config()
    # print the key corresponding to salomeTools version
    msg = src.printcolors.printcHeader( _("Version: ") ) + \
          cfg.INTERNAL.sat_version
    return msg
  
def get_help():
    """get general help colored string
    """
    # read the config 
    msg = get_version() + "\n\n"
    msg += src.printcolors.printcHeader(_("Usage: ")) + \
          "sat [generic_options] <command> [product] [command_options]\n\n"
    msg += Sat()._getParser().get_help() + "\n"
    msg += src.printcolors.printcHeader(_("Available commands are:")) + "\n\n"
    for command in _COMMANDS_NAMES:
        msg += " - %s\n" % (command)
    msg += "\n"
    # Explain how to get the help for a specific command
    msg += src.printcolors.printcHeader(
           _("Getting the help for a specific command: ")) + \
           "sat --help <command>\n"
    return msg

def print_help():
    """prints salomeTools general help
    """
    msg = get_help() 
    if isStdoutPipe():
        # clean color if the terminal is redirected by user
        # ex: sat compile appli > log.txt
        msg = src.printcolors.cleancolor(msg)  
    print(msg)
    return

def write_exception(exc):
    '''write in stderr exception in case of error in a command
    
    :param exc exception: the exception to print
    '''
    sys.stderr.write("\n***** ")
    sys.stderr.write(src.printcolors.printcError("salomeTools ERROR:"))
    sys.stderr.write("\n" + str(exc) + "\n")




