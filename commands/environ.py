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

# list of available shells with extensions
C_SHELLS = { "bash": "sh", "bat": "bat", "cfg" : "cfg" }
C_ALL_SHELL = [ "bash", "bat", "cfg" ]


########################################################################
# Command class
########################################################################
class Command(_BaseCommand):
  """
  The environ command generates the environment files of your application.

  | examples:
  | >> sat environ SALOME
  """
  
  name = "environ"
  
  def getParser(self):
    """Define all options for command 'sat environ <options>'"""
    parser = self.getParserWithHelp()
    parser.add_option('', 'shell', 'list2', 'shell',
        _("Optional: Generates the environment files for the given format: "
          "bash (default), bat (for windows), cfg (salome context file) or all."), [])
    parser.add_option('p', 'products', 'list2', 'products',
        _("Optional: Includes only the specified products."))
    parser.add_option('', 'prefix', 'string', 'prefix',
        _("Optional: Specifies the prefix for the environment files."), "env")
    parser.add_option('t', 'target', 'string', 'out_dir',
        _("Optional: Specifies the directory path where to put the environment files."),
        None)
    return parser

  def run(self, cmd_arguments):
    """method called for command 'sat environ <options>'"""
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

    # check that the command was called with an application
    UTS.check_config_has_application(config).raiseIfKo()
    
    if options.products is None:
        environ_info = None
    else:
        # add products specified by user (only products 
        # included in the application)
        environ_info = filter(lambda l:
                              l in config.APPLICATION.products.keys(),
                              options.products)
    
    if options.shell == []:
        shell = ["bash"]
        if src.architecture.is_windows():
            shell = ["bat"]
    else:
        shell = options.shell
    
    out_dir = options.out_dir
    if out_dir:
        out_dir = os.path.abspath(out_dir)
    
    write_all_source_files(config, logger, out_dir=out_dir, shells=shell,
                           prefix=options.prefix, env_info=environ_info)
    logger.info("\n")
    #TODO return code

def write_all_source_files(config,
                           logger,
                           out_dir=None,
                           src_root=None,
                           silent=False,
                           shells=["bash"],
                           prefix="env",
                           env_info=None):
    """Generates the environment files.
    
    :param config: (Config) The global configuration
    :param logger: (Logger)
      The logger instance to use for the display and logging
    :param out_dir: (str) 
      The path to the directory where the files will be put
    :param src_root: (str) 
      The path to the directory where the sources are
    :param silent: (bool) 
      If True, do not print anything in the terminal
    :param shells: (list) The list of shells to generate
    :param prefix: (str) The prefix to add to the file names.
    :param env_info: (str) The list of products to add in the files.
    :return: (list) The list of the generated files.
    """
        
    if not out_dir:
        out_dir = config.APPLICATION.workdir

    if not os.path.exists(out_dir):
        raise Exception(_("Target directory not found: %s") % out_dir)

    if not silent:
        logger.info(_("Creating environment files for %s\n") % \
                     UTS.header(config.APPLICATION.name))
        logger.info("  %s = %s\n\n" % (_("Target"), out_dir))
    
    shells_list = []
    all_shells = C_ALL_SHELL
    if "all" in shells:
        shells = all_shells
    else:
        shells = filter(lambda l: l in all_shells, shells)

    for shell in shells:
        if shell not in C_SHELLS:
            logger.warning(_("Unknown shell: %s\n") % shell)
        else:
            shells_list.append(src.environment.Shell(shell, C_SHELLS[shell]))
    
    writer = src.environment.FileEnvWriter(config,
                                           logger,
                                           out_dir,
                                           src_root,
                                           env_info)
    writer.silent = silent
    files = []
    for_build = True
    for_launch = False
    for shell in shells_list:
        files.append(writer.write_env_file("%s_launch.%s" %
                                           (prefix, shell.extension),
                                           for_launch,
                                           shell.name))
        files.append(writer.write_env_file("%s_build.%s" %
                                           (prefix, shell.extension),
                                           for_build,
                                           shell.name))

    return files
