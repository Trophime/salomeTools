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
import src.product as PROD
import src.compilation as COMP
from src.salomeTools import _BaseCommand

########################################################################
# Command class
########################################################################
class Command(_BaseCommand):
  """
  The makeinstall command executes the 'make install' command in the build directory.
  In case of product constructed using a script (build_source : 'script'), 
  then the makeinstall command do nothing.
  
  | Examples:
  | >> sat makeinstall SALOME --products KERNEL,GUI
  """
  
  name = "makeinstall"
  
  def getParser(self):
    """Define all options for the command 'sat makeinstall <options>'"""
    parser = self.getParserWithHelp()
    parser.add_option('p', 'products', 'list2', 'products',
        _('Optional: products to install. This option can be'
        ' passed several time to install several products.'))
    return parser

  def run(self, cmd_arguments):
    """method called for command 'sat makeinstall <options>'"""
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

    # Get the list of products to treat
    products_infos = self.get_products_list(options, config)

    # Print some informations
    logger.info(_('Executing the make install command in the build directories of the application %s\n') % \
                UTS.label(config.VARS.application))
    
    info = [(_("BUILD directory"),
             os.path.join(config.APPLICATION.workdir, 'BUILD'))]
    logger.info(UTS.formatTuples(info))
    
    # Call the function that will loop over all the products and execute
    # the right command(s)
    res = self.makeinstall_all_products(products_infos)
    
    good_result = sum(1 for r in res if r.isOk())
    nbExpected = len(products_infos)
    msgCount = "(%d/%d)" % (good_result, nbExpected)
    if good_result == nbExpected:
      status = "OK"
      msg = _("command makeinstall")
      logger.info("\n%s %s: <%s>.\n" % (msg, msgCount, status))
    else:
      status = "KO"
      msg = _("command makeinstall, some products have failed")
      logger.info("\n%s %s: <%s>.\n" % (msg, msgCount, status))

    return RCO.ReturnCode(status, "%s %s" % (msg, msgCount))

  def makeinstall_all_products(self, products_infos):
    """
    Execute the proper configuration commands 
    in each product build directory.

    :param products_info: (list) 
      List of (str, Config) => (product_name, product_info)
    :return: (list of RCO.ReturnCode) list of OK if it succeed
    """
    res = []
    for p_name_info in products_infos:
      res.append(self.makeinstall_product(p_name_info))
    return res

  def makeinstall_product(self, p_name_info):
    """
    Execute the proper configuration command(s) 
    in the product build directory.
    
    :param p_name_info: (tuple) 
      (str, Config) => (product_name, product_info)
    :param config: (Config) The global configuration
    :param logger: (Logger) 
      The logger instance to use for the display and logging
    :return: (RCO.ReturnCode)
    """
    # shortcuts
    runner = self.getRunner()
    config = self.getConfig()
    logger = self.getLogger()
    options = self.getOptions()
    
    p_name, p_info = p_name_info
    
    # Logging
    header = _("Make install of %s") % UTS.label(p_name)
    logger.logStep_begin(header) # needs logStep_end

    # Do nothing if he product is not compilable
    if ("properties" in p_info and \
        "compilation" in p_info.properties and \
        p_info.properties.compilation == "no"):
      logger.logStep("ignored")
      return RCO.ReturnCode("OK", "product %s is not compilable" % p_name)

    # Instantiate the class that manages all the construction commands
    # like cmake, make, make install, make test, environment management, etc...
    builder = COMP.Builder(config, logger, p_info)
    
    # Prepare the environment
    logger.logStep("PREPARE ENV")
    res = builder.prepare()
    logger.logStep(res)
    
    # Execute buildconfigure, configure if the product is autotools
    # Execute cmake if the product is cmake
    if not PROD.product_has_script(p_info):
      logger.logStep("MAKE INSTALL")
      res_m = builder.install()
      logger.logStep(res_m)
      res += res_m

    return res
