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
import src.product as PROD
import src.compilation as COMP
from src.salomeTools import _BaseCommand

########################################################################
# Command class
########################################################################
class Command(_BaseCommand):
  """
  The configure command executes in the build directory commands
  corresponding to the compilation mode of the application products.
  The possible compilation modes are 'cmake', 'autotools', or 'script'.

  | Here are the commands to be run:
  |   autotools: >> build_configure and configure
  |   cmake:     >> cmake
  |   script:    (do nothing)
  | 
  | examples:
  | >> sat configure SALOME --products KERNEL,GUI,PARAVIS
  """
  
  name = "configure"
  
  def getParser(self):
    """Define all options for command 'sat configure <options>'"""
    parser = self.getParserWithHelp()
    parser.add_option('p', 'products', 'list2', 'products',
        _('Optional: products to configure. This option can be'
        ' passed several time to configure several products.'))
    parser.add_option('o', 'option', 'string', 'option',
        _('Optional: Option to add to the configure or cmake command.'), "")
    return parser

  def run(self, cmd_arguments):
    """method called for command 'sat configure <options>'"""
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
    logger.info(_('Configuring the sources of the application %s\n') % 
                UTS.label(config.VARS.application))
    
    info = [(_("BUILD directory"),
             os.path.join(config.APPLICATION.workdir, 'BUILD'))]
    UTS.logger_info_tuples(logger, info)
    
    # Call the function that will loop over all the products and execute
    # the right command(s)
    if options.option is None:
        options.option = ""
    res = configure_all_products(config, products_infos, options.option, logger)
    
    # Print the final state
    nb_products = len(products_infos)
    if res == 0:
        final_status = "<OK>"
    else:
        final_status = "<KO>"
   
    logger.info(_("\nConfiguration: %(status)s (%(1)d/%(2)d)\n") % \
        { 'status': final_status, 
          '1': nb_products - res,
          '2': nb_products }, 1)    
    
    return res 


def get_products_list(options, cfg, logger):
    """
    method that gives the product list with their informations from 
    configuration regarding the passed options.
    
    :param options: (Options) 
      The Options instance that stores the commands arguments
    :param cfg: (Config) The global configuration
    :param logger: (Logger) 
      The logger instance to use for the display and logging
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
                raise Exception(
                    _("Product %(product)s not defined in application %(application)s") %
                    {'product': p, 'application': cfg.VARS.application} )
    
    # Construct the list of tuple containing 
    # the products name and their definition
    products_infos = PROD.get_products_infos(products, cfg)
    
    products_infos = [pi for pi in products_infos \
      if not(PROD.product_is_native(pi[1]) or PROD.product_is_fixed(pi[1]))]
    
    return products_infos

def configure_all_products(config, products_infos, conf_option, logger):
    """
    Execute the proper configuration commands 
    in each product build directory.

    :param config: (Config) The global configuration
    :param products_info: (list) 
      List of (str, Config) => (product_name, product_info)
    :param conf_option: (str) The options to add to the command
    :param logger: (Logger) The logger instance to use for the display and logging
    :return: (int) the number of failing commands.
    """
    res = 0
    for p_name_info in products_infos:
        res_prod = configure_product(p_name_info, conf_option, config, logger)
        if res_prod != 0:
            res += 1 
    return res

def configure_product(p_name_info, conf_option, config, logger):
    """
    Execute the proper configuration command(s) 
    in the product build directory.
    
    :param p_name_info: (tuple) 
      (str, Config) => (product_name, product_info)
    :param conf_option: (str) The options to add to the command
    :param config: (Config) The global configuration
    :param logger: (Logger) 
      The logger instance to use for the display and logging
    :return: (int) 1 if it fails, else 0.
    """
    
    p_name, p_info = p_name_info
    
    # Logging
    header = _("Configuration of %s") % UTS.label(p_name)
    header += " %s " % ("." * (20 - len(p_name)))
    logger.info(header)
    
    # Do nothing if he product is not compilable
    if ("properties" in p_info and \
        "compilation" in p_info.properties and \
        p_info.properties.compilation == "no"):
          
        UTS.log_step(logger, header, "ignored")
        logger.info("\n")
        return 0

    # Instantiate the class that manages all the construction commands
    # like cmake, make, make install, make test, environment management, etc...
    builder = COMP.Builder(config, logger, p_info)
    
    # Prepare the environment
    UTS.log_step(logger, header, "PREPARE ENV")
    res_prepare = builder.prepare()
    UTS.log_res_step(logger, res_prepare)
    
    # Execute buildconfigure, configure if the product is autotools
    # Execute cmake if the product is cmake
    res = 0
    if PROD.product_is_autotools(p_info):
        UTS.log_step(logger, header, "BUILDCONFIGURE")
        res_bc = builder.build_configure()
        UTS.log_res_step(logger, res_bc)
        res += res_bc
        UTS.log_step(logger, header, "CONFIGURE")
        res_c = builder.configure(conf_option)
        UTS.log_res_step(logger, res_c)
        res += res_c
    if PROD.product_is_cmake(p_info):
        UTS.log_step(logger, header, "CMAKE")
        res_cm = builder.cmake(conf_option)
        UTS.log_res_step(logger, res_cm)
        res += res_cm
    
    # Log the result
    if res > 0:
        logger.info("\r%s%s" % (header, " " * 20))
        logger.info("\r" + header + "<KO>")
        logger.debug("==== <KO> in configuration of %s\n" % p_name)
    else:
        logger.info("\r%s%s" % (header, " " * 20))
        logger.info("\r" + header + "<OK>")
        logger.debug("==== <OK> in configuration of %s\n" % p_name)
    logger.info("\n")

    return res
