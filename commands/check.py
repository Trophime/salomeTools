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

import src.debug as DBG
import src.returnCode as RCO
import src.utilsSat as UTS
import src.product as PROD
import src.compilation as COMP
from src.salomeTools import _BaseCommand

CHECK_PROPERTY = "has_unit_tests"

########################################################################
# Command class
########################################################################
class Command(_BaseCommand):
  """
  The check command executes the 'check' command in the build directory of 
  all the products of the application.
  It is possible to reduce the list of products to check
  by using the --products option

  | examples:
  | >> sat check SALOME --products KERNEL,GUI,GEOM
  """
  
  name = "check"
  
  def getParser(self):
    """Define all options for the check command 'sat check <options>'"""
    parser = self.getParserWithHelp()
    parser.add_option('p', 'products', 'list2', 'products',
        _("""\
Optional: products to configure.
          This option can be passed several time to configure several products."""))
    return parser

  def run(self, cmd_arguments):
    """method called for command 'sat check <options>'"""
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
    products_infos = get_products_list(options, config, logger)
    
    # Print some informations
    msg = _('Executing the check command in the build directories of the application')
    logger.info("%s %s\n" % (msg, UTS.label(config.VARS.application)))
    
    info = [(_("BUILD directory"),
             os.path.join(config.APPLICATION.workdir, 'BUILD'))]
    UTS.logger_info_tuples(logger, info)
    
    # Call the function that will loop over all the products and execute
    # the right command(s)
    res = check_all_products(config, products_infos, logger)
    
    # Print the final state
    nb_products = len(products_infos)
    if res == 0:
        final_status = "<OK>"
    else:
        final_status = "<KO>"
   
    logger.info(_("\nCheck: %(status)s (%(1)d/%(2)d)\n") % \
        { 'status': final_status, 
          '1': nb_products - res,
          '2': nb_products })    
    
    return res 


def get_products_list(options, cfg, logger):
    """
    method that gives the product list with their informations from 
    configuration regarding the passed options.
    
    :param options: (Options) The Options instance that stores 
      the commands arguments
    :param cfg: (Config) The global configuration
    :param logger: (Logger) The logger instance to use 
      for the display and logging
    :return: (list) The list of (product name, product_informations).
    """
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
                msg = _("Product %(1)s not defined in application %(2)s") % \
                      { '1': p, '2': cfg.VARS.application}
                raise Exception(msg)
    
    # Construct the list of tuple containing 
    # the products name and their definition
    products_infos = PROD.get_products_infos(products, cfg)
    
    products_infos = [pi for pi in products_infos \
       if not(PROD.product_is_native(pi[1]) or PROD.product_is_fixed(pi[1])) ]
    
    return products_infos

def check_all_products(config, products_infos, logger):
    """
    Execute the proper configuration commands 
    in each product build directory.

    :param config: (Config) The global configuration
    :param products_info: (list) 
      List of (str, Config) => (product_name, product_info)
    :param logger: (Logger) 
      The logger instance to use for the display and logging
    :return: (int) the number of failing commands.
    """
    res = 0
    for p_name_info in products_infos:
        res_prod = check_product(p_name_info, config, logger)
        if res_prod != 0:
            res += 1 
    return res

def check_product(p_name_info, config, logger):
    """
    Execute the proper configuration command(s) 
    in the product build directory.
    
    :param p_name_info: (tuple) 
      (str, Config) => (product_name, product_info)
    :param config: (Config) The global configuration
    :param logger: (Logger) 
      The logger instance to use for the display and logging
    :return: (int) 1 if it fails, else 0.
    """
    
    p_name, p_info = p_name_info

    header = _("Check of %s") % UTS.label(p_name)
    header += " %s " % ("." * (20 - len(p_name)))
    logger.info(header)

    # Verify if the command has to be launched or not
    ignored = False
    msg += ""
    if not UTS.get_property_in_product_cfg(p_info, CHECK_PROPERTY):
        msg += _("The product %s is defined as not having tests: product ignored.\n") % p_name
        ignored = True
    if "build_dir" not in p_info:
        msg += _("The product %s have no 'build_dir' key: product ignored.\n") % p_name
        ignored = True
    if not PROD.product_compiles(p_info):
        msg += _("The product %s is defined as not compiling: product ignored.\n") % p_name
        ignored = True
    
    logger.info("%s\n" % msg)
    # Get the command to execute for script products
    cmd_found = True
    command = ""
    if PROD.product_has_script(p_info) and not ignored:
        command = UTS.get_config_key(p_info, "test_build", "Not found")
        if command == "Not found":
            cmd_found = False
            msg = _("""\
The product %s is defined as having tests.
But it is compiled using a script and the key 'test_build'
is not defined in the definition of %(name)\n""") % p_name
            logger.warning(msg)
                
    if ignored or not cmd_found:
        UTS.log_step(logger, header, "ignored")
        logger.debug("==== %s %s\n" % (p_name, "IGNORED"))
        if not cmd_found:
            return 1
        return 0
    
    # Instantiate the class that manages all the construction commands
    # like cmake, check, make install, make test, environment management, etc...
    builder = COMP.Builder(config, logger, p_info)
    
    # Prepare the environment
    UTS.log_step(logger, header, "PREPARE ENV")
    res_prepare = builder.prepare()
    UTS.log_res_step(logger, res_prepare)
    
    len_end_line = 20

    # Launch the check    
    UTS.log_step(logger, header, "CHECK")
    res = builder.check(command=command)
    UTS.log_res_step(logger, res)
    
    # Log the result
    if res > 0:
        logger.info("\r%s%s" % (header, " " * len_end_line))
        logger.info("\r" + header + "<KO>\n")
        logger.debug("==== <KO> in check of %s\n" % p_name)
    else:
        logger.info("\r%s%s" % (header, " " * len_end_line))
        logger.info("\r" + header + "<OK>\n")
        logger.debug("==== <OK> in check of %s\n" % p_name)
    logger.info("\n")

    return res

