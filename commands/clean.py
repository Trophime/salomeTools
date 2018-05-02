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

import re

import src.debug as DBG
import src.returnCode as RCO
import src.utilsSat as UTS
from src.salomeTools import _BaseCommand

# Compatibility python 2/3 for input function
# input stays input for python 3 and input = raw_input for python 2
try: 
    input = raw_input
except NameError: 
    pass

PROPERTY_EXPRESSION = "^.+:.+$"

########################################################################
# Command class
########################################################################
class Command(_BaseCommand):
  """
  The clean command suppresses the source, build, or install directories 
  of the application products.
  Use the options to define what directories you want to suppress and 
  to reduce the list of products

  | examples:
  | >> sat clean SALOME --build --install --properties is_salome_module:yes
  """
  
  name = "clean"
  
  def getParser(self):
    """Define all options for the command 'sat clean <options>'"""
    parser = self.getParserWithHelp()
    parser.add_option('p', 'products', 'list2', 'products',
        _('Optional: Products to clean. This option can be'
        ' passed several time to clean several products.'))
    parser.add_option('', 'properties', 'string', 'properties',
        _('Optional: Filter the products by their properties.\n'
          '\tSyntax: --properties <property>:<value>'))
    parser.add_option('s', 'sources', 'boolean', 'sources', 
        _("Optional: Clean the product source directories."))
    parser.add_option('b', 'build', 'boolean', 'build', 
        _("Optional: Clean the product build directories."))
    parser.add_option('i', 'install', 'boolean', 'install', 
        _("Optional: Clean the product install directories."))
    parser.add_option('a', 'all', 'boolean', 'all', 
        _("Optional: Clean the product source, build and install directories."))
    parser.add_option('', 'sources_without_dev', 'boolean', 'sources_without_dev', 
        _("Optional: do not clean the products in development mode."))
    return parser    

  
  def run(self, cmd_arguments):
    """method called for command 'sat clean <options>'"""
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

    # check that the command has been called with an application
    UTS.check_config_has_application(config).raiseIfKo()

    # Verify the --properties option
    if options.properties:
        oExpr = re.compile(PROPERTY_EXPRESSION)
        if not oExpr.search(options.properties):
            msg = _("""\
The '--properties' options must have the following syntax:
  --properties <property>:<value>\n""")
            logger.error(msg)
            options.properties = None
            

    # Get the list of products to threat
    products_infos = self.get_products_list(options, config, logger)

    # Construct the list of directories to suppress
    l_dir_to_suppress = []
    if options.all:
        l_dir_to_suppress += (get_source_directories(products_infos, 
                                            options.sources_without_dev) +
                             get_build_directories(products_infos) + 
                             get_install_directories(products_infos))
    else:
        if options.install:
            l_dir_to_suppress += get_install_directories(products_infos)
        
        if options.build:
            l_dir_to_suppress += get_build_directories(products_infos)
            
        if options.sources or options.sources_without_dev:
            l_dir_to_suppress += get_source_directories(products_infos, 
                                                options.sources_without_dev)
    
    if len(l_dir_to_suppress) == 0:
        sat_command = ("sat -h clean")
        msg = _("Nothing to suppress, Please specify what you want to suppress.")
        logger.error(msg + "\nsee: '%s'\n" % sat_command)
        return RCO.ReturnCode("KO", "specify what you want to suppress")
    
    # Check with the user if he really wants to suppress the directories
    if not runner.options.batch:
        msg = _("Remove the following directories ?\n")
        for directory in l_dir_to_suppress:
            msg += "  %s\n" % directory
        logger.info(msg)
        rep = input(_("Are you sure you want to continue? [Yes/No] "))
        if rep.upper() != _("YES"):
            return RCO.ReturnCode("OK", "user do not want to continue")
    
    # Suppress the list of paths
    suppress_directories(l_dir_to_suppress, logger)
    
    return RCO.ReturnCode("OK", "clean done")
    

def get_source_directories(products_infos, without_dev):
    """
    Returns the list of directory source paths corresponding to the list of 
    product information given as input. If without_dev (bool), then
    the dev products are ignored.
    
    :param products_infos: (list) 
      The list of (name, config) corresponding to one product.
    :param without_dev: (boolean) If True, then ignore the dev products.
    :return: (list) the list of source paths.
    """
    l_dir_source = []
    for __, product_info in products_infos:
        if product_has_dir(product_info, without_dev):
            l_dir_source.append(src.Path(product_info.source_dir))
    return l_dir_source

def get_build_directories(products_infos):
    """
    Returns the list of directory build paths corresponding to the list of 
    product information given as input.
    
    :param products_infos: (list)
      The list of (name, config) corresponding to one product.
    :return: (list) the list of build paths.
    """
    l_dir_build = []
    for __, product_info in products_infos:
        if product_has_dir(product_info):
            if "build_dir" in product_info:
                l_dir_build.append(src.Path(product_info.build_dir))
    return l_dir_build

def get_install_directories(products_infos):
    """
    Returns the list of directory install paths corresponding to the list of 
    product information given as input.
    
    :param products_infos: (list) 
      The list of (name, config) corresponding to one product.
    :return: (list) the list of install paths.
    """
    l_dir_install = []
    for __, product_info in products_infos:
        if product_has_dir(product_info):
            l_dir_install.append(src.Path(product_info.install_dir))
    return l_dir_install

def product_has_dir(product_info, without_dev=False):
    """
    Returns a boolean at True if there is a source, build and install
    directory corresponding to the product described by product_info.
    
    :param products_info: (Config) 
      The config corresponding to the product.
    :return: (bool)
      True if there is a source, build and install
      directory corresponding to the product described by product_info.
    """
    if (src.product.product_is_native(product_info) or 
                            src.product.product_is_fixed(product_info)):
        return False
    if without_dev:
        if src.product.product_is_dev(product_info):
            return False
    return True
    
def suppress_directories(l_paths, logger):
    """Suppress the paths given in the list in l_paths.
    
    :param l_paths: (list) The list of Path to be suppressed
    :param logger: (Logger) 
      The logger instance to use for the display and logging
    """    
    for path in l_paths:
        strpath = str(path)
        if not path.isdir():
            msg = _("The path %s does not exists (or is not a directory)\n") % strpath
            logger.warning(msg)
        else:
            logger.info(_("Removing %s ...") % strpath )
            path.rm()
            logger.info('<OK>\n')

