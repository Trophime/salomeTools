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
import re

import src.debug as DBG
import src.returnCode as RCO
import src.utilsSat as UTS
import src.product as PROD
import src.compilation as COMP
import src.architecture as ARCH
from src.salomeTools import _BaseCommand

########################################################################
# Command class
########################################################################
class Command(_BaseCommand):
  """
  The make command executes the 'make' command in the build directory.

  | Examples:
  | >> sat make SALOME --products Python,KERNEL,GUI
  """
  
  name = "make"
  
  def getParser(self):
    """Define all options for the command 'sat make <options>'"""
    parser = self.getParserWithHelp()
    parser.add_option('p', 'products', 'list2', 'products',
        _('Optional: products to configure. This option can be'
          ' passed several time to configure several products.'))
    parser.add_option('o', 'option', 'string', 'option',
        _('Optional: Option to add to the make command.'), "")   
    return parser

  def run(self, cmd_arguments):
    """method called for command 'sat make <options>'"""
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
    msg = _('Executing the make command in the build directories of the application %s') % \
          UTS.label(config.VARS.application)
    info = [(_("BUILD directory"), os.path.join(config.APPLICATION.workdir, 'BUILD'))]
    msg += "\n" + UTS.formatTuples(info)
    logger.info(msg)
    
    # Call the function that will loop over all the products and execute
    # the right command(s)
    if options.option is None:
        options.option = ""
    res = make_all_products(config, products_infos, options.option, logger)
    
    good_result = sum(1 for r in res if r.isOk())
    nbExpected = len(products_infos)
    msgCount = "(%d/%d)" % (good_result, nbExpected)
    if good_result == nbExpected:
      status = "OK"
      msg = _("command make")
      logger.info("\n%s %s: <%s>.\n" % (msg, msgCount, status))
    else:
      status = "KO"
      msg = _("command make, some products have failed")
      logger.info("\n%s %s: <%s>.\n" % (msg, msgCount, status))

    return RCO.ReturnCode(status, "%s %s" % (msg, msgCount))

def make_all_products(config, products_infos, make_option, logger):
    """
    Execute the proper configuration commands 
    in each product build directory.

    :param config: (Config) The global configuration
    :param products_info: (list) 
      List of (str, Config) => (product_name, product_info)
    :param make_option: (str) The options to add to the command
    :param logger: (Logger) 
      The logger instance to use for the display and logging
    :return: (list of RCO.ReturnCode)
    """
    res = []
    for p_name_info in products_infos:
      res.append(make_product(p_name_info, make_option, config, logger))
    return res

def make_product(p_name_info, make_option, config, logger):
    """
    Execute the proper configuration command(s) 
    in the product build directory.
    
    :param p_name_info: (tuple) (str, Config) => (product_name, product_info)
    :param make_option: (str) The options to add to the command
    :param config: (Config) The global configuration
    :param logger: (Logger) 
      The logger instance to use for the display and logging
    :return: (int) 1 if it fails, else 0.
    """
    
    p_name, p_info = p_name_info
    
    # Logging
    header = _("Make of %s") % UTS.label(p_name)
    logger.logStep_begin(header) # needs logStep_end

    # Do nothing if he product is not compilable
    if ("properties" in p_info and \
        "compilation" in p_info.properties and \
        p_info.properties.compilation == "no"):
        logger.logStep("ignored")
        return 0

    # Instantiate the class that manages all the construction commands
    # like cmake, make, make install, make test, environment management, etc...
    builder = COMP.Builder(config, logger, p_info)
    
    # Prepare the environment
    logger.logStep("PREPARE ENV")
    res_prepare = builder.prepare()
    logger.logStep(res_prepare)
    
    # Execute buildconfigure, configure if the product is autotools
    # Execute cmake if the product is cmake

    nb_proc, make_opt_without_j = get_nb_proc(p_info, config, make_option)
    logger.logStep("MAKE -j" + str(nb_proc))
    
    if ARCH.is_windows():
        res = builder.wmake(nb_proc, make_opt_without_j)
    else:
        res = builder.make(nb_proc, make_opt_without_j)

    logger.logStep(res)
    return res

def get_nb_proc(product_info, config, make_option):
    
    opt_nb_proc = None
    new_make_option = make_option
    if "-j" in make_option:
        oExpr = re.compile("-j[0-9]+")
        found = oExpr.search(make_option)
        opt_nb_proc = int(re.findall('\d+', found.group())[0])
        new_make_option = make_option.replace(found.group(), "")
    
    nbproc = -1
    if "nb_proc" in product_info:
        # nb proc is specified in module definition
        nbproc = product_info.nb_proc
        if opt_nb_proc and opt_nb_proc < product_info.nb_proc:
            # use command line value only if it is lower than module definition
            nbproc = opt_nb_proc
    else:
        # nb proc is not specified in module definition
        if opt_nb_proc:
            nbproc = opt_nb_proc
        else:
            nbproc = config.VARS.nb_proc
    
    assert nbproc > 0
    return nbproc, new_make_option
