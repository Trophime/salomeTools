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

import src.debug as DBG
import src.returnCode as RCO
import src.utilsSat as UTS
from src.salomeTools import _BaseCommand
import src.configManager as CFGMGR
import src.system as SYSS


########################################################################
# Command class
########################################################################
class Command(_BaseCommand):
  # ' | ' is used in sphinx  apidoc interpretation
  """
  The config command allows manipulation and operation on config '.pyconf' files.

  | Examples:
  | >> sat config --list
  | >> sat config SALOME --edit
  | >> sat config SALOME --copy SALOME-new
  | >> sat config SALOME --value VARS
  | >> sat config SALOME --debug VARS
  | >> sat config SALOME --info ParaView
  | >> sat config SALOME --show_patchs
  """
  
  name = "config"
  
  def getParser(self):
    """Define all options for command 'sat config <options>'"""
    parser = self.getParserWithHelp()
    parser.add_option('v', 'value', 'string', 'value',
        _("Optional: print the value of CONFIG_VARIABLE."))
    parser.add_option('d', 'debug', 'string', 'debug',
        _("Optional: print the debugging value of CONFIG_VARIABLE."))
    parser.add_option('e', 'edit', 'boolean', 'edit',
        _("Optional: edit the product configuration file."))
    parser.add_option('i', 'info', 'string', 'info',
        _("Optional: get information on a product."))
    parser.add_option('l', 'list', 'boolean', 'list',
        _("Optional: list all available applications."))
    parser.add_option('p', 'show_patchs', 'boolean', 'show_patchs',
        _("Optional: synthetic view of all patches used in the application"))
    parser.add_option('c', 'copy', 'boolean', 'copy',
        _("""\
Optional: copy a config file (.pyconf) to the personal config files directory.
Warning: the included files are not copied.
If a name is given the new config file takes the given name."""))
    parser.add_option('n', 'no_label', 'boolean', 'no_label',
        _("Internal use: do not print labels, Works only with --value and --list."))
    parser.add_option('o', 'completion', 'boolean', 'completion',
        _("Internal use: print only keys, works only with --value."))
    parser.add_option('s', 'schema', 'boolean', 'schema',
        _("Internal use."))
    return parser

  def run(self, cmd_arguments):
    """method called for command 'sat config <options>'"""
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

    if config is None:
      return RCO.ReturnCode("KO", "config is None")
      
    # Only useful for completion mechanism : print the keys of the config
    if options.schema:
        get_config_children(config, args)
        return RCO.ReturnCode("OK", "completion mechanism")
    
    # case : print a value of the config
    if options.value:
        if options.value == ".":
            # if argument is ".", print all the config
            msg = ""
            for val in sorted(config.keys()):
                msg += CFGMGR.getStrConfigValue(config, val, not options.no_label)
        else:
            msg = CFGMGR.getStrConfigValue(config, options.value, not options.no_label, 
                                           level=0, show_full_path=False)
        logger.info(msg)

    if options.debug:
        msg = CFGMGR.getStrConfigDebug(config, str(options.debug), not options.no_label, 
                                       level=0, show_full_path=False)
        logger.info(msg)
    
    # case : edit user pyconf file or application file
    elif options.edit:
        editor = config.USER.editor
        if ('APPLICATION' not in config and
            'open_application' not in config): # edit user pyconf
            usercfg = os.path.join(config.VARS.personalDir, 'SAT.pyconf')
            logger.info(_("Opening %s\n") % usercfg)
            SYSS.show_in_editor(editor, usercfg, logger)
        else:
            # search for file <application>.pyconf and open it
            for path in config.PATHS.APPLICATIONPATH:
                pyconf_path = os.path.join(path, config.VARS.application + ".pyconf")
                if os.path.exists(pyconf_path):
                    logger.info(_("Opening %s\n") % pyconf_path)
                    SYSS.show_in_editor(editor, pyconf_path, logger)
                    break
    
    # case : give information about the product in parameter
    elif options.info:
        UTS.check_config_has_application(config).raiseIfKo()
        cfg_products = config.APPLICATION.products
        if options.info in cfg_products:
            CFGMGR.show_product_info(config, options.info, logger)
            return RCO.ReturnCode("OK", "product '%s' found in products" % options.info)
        msg = _("product %s is not defined in application %s.") % \
                (options.info, UTS.info(config.VARS.application))
        logger.error(msg)
        return RCO.ReturnCode("KO", msg)
    
    # case : copy an existing <application>.pyconf 
    # to ~/.salomeTools/Applications/LOCAL_<application>.pyconf
    elif options.copy:
        # product is required
        UTS.check_config_has_application(config).raiseIfKo()

        # get application file path 
        source = config.VARS.application + '.pyconf'
        source_full_path = ""
        for path in config.PATHS.APPLICATIONPATH:
            # ignore personal directory
            if path == config.VARS.personalDir:
                continue
            # loop on all directories that can have pyconf applications
            zz = os.path.join(path, source)
            if os.path.exists(zz):
                source_full_path = zz
                break

        if len(source_full_path) == 0:
            raise Exception(
                _("Config file for product %s not found\n") % source )
        else:
            if len(args) > 0:
                # a name is given as parameter, use it
                dest = args[0]
            elif 'copy_prefix' in config.INTERNAL.config:
                # use prefix
                dest = (config.INTERNAL.config.copy_prefix 
                        + config.VARS.application)
            else:
                # use same name as source
                dest = config.VARS.application
                
            # the full path
            dest_file = os.path.join(
                config.VARS.personalDir, 'Applications', dest + '.pyconf' )
            if os.path.exists(dest_file):
                raise Exception(
                    _("A personal application '%s' already exists") % dest )
            
            # perform the copy
            shutil.copyfile(source_full_path, dest_file)
            logger.info(_("%s has been created.\n") % dest_file)
    
    # case : display all the available pyconf applications
    elif options.list:
      lproduct = []
      # search in all directories that can have pyconf applications
      msg = ""
      for path in config.PATHS.APPLICATIONPATH:
        # print a header
        if not options.no_label:
          msg += UTS.header("\n------ %s\n" % path)
        if not os.path.exists(path):
          msg += (UTS.red( _("Directory not found")) + "\n" )
        else:
          for f in sorted(os.listdir(path)):
            # ignore file that does not ends with .pyconf
            if not f.endswith('.pyconf'):
              continue
            appliname = f[:-len('.pyconf')]
            if appliname not in lproduct:
              lproduct.append(appliname)
              if path.startswith(config.VARS.personalDir):
                msg += "%s<red>*<reset>\n" % appliname
              else:
                msg += "%s\n" % appliname
      logger.info(msg)

      if len(lproduct) == 0:
        aFile = os.path.join(config.VARS.datadir, 'local.pyconf')
        msg = """\
no existing product
may be you have to set some PROJECTS.project_file_paths in file
%s""" % aFile
        logger.warning(msg)
        return RCO.ReturnCode("OK", msg)
      else:
        return RCO.ReturnCode("OK", "config -l command done", lproduct)
                
    # case : give a synthetic view of all patches used in the application
    elif options.show_patchs:
        UTS.check_config_has_application(config).raiseIfKo()
        # Print some informations
        logger.info(_('Show the patchs of application %s\n') % \
                      UTS.label(config.VARS.application))
        CFGMGR.show_patchs(config, logger)
    
    # case: print all the products name of the application (internal use for completion)
    elif options.completion:
        for product_name in config.APPLICATION.products.keys():
            logger.info("%s\n" % product_name)
          
    return RCO.ReturnCode("OK", "config command done")
