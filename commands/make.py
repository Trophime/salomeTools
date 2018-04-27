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
from src.salomeTools import _BaseCommand

########################################################################
# Command class
########################################################################
class Command(_BaseCommand):
  """\
  The make command executes the 'make' command in the build directory.

  examples:
    >> sat make SALOME --products Python,KERNEL,GUI
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
    src.check_config_has_application( config )

    # Get the list of products to treat
    products_infos = get_products_list(options, config, logger)
    
    # Print some informations
    logger.info(
        _('Executing the make command in the build directories of the application %s\n') % \
        UTS.label(config.VARS.application))
    
    info = [(_("BUILD directory"), os.path.join(config.APPLICATION.workdir, 'BUILD'))]
    UTS.logger_info_tuples(logger, info)
    
    # Call the function that will loop over all the products and execute
    # the right command(s)
    if options.option is None:
        options.option = ""
    res = make_all_products(config, products_infos, options.option, logger)
    
    # Print the final state
    nb_products = len(products_infos)
    if res == 0:
        final_status = "OK"
    else:
        final_status = "KO"
   
    msg = _("\nMake: <%s> (%d/%d)\n") % (final_status, nb_products - res, nb_products)
    logger.info(msg)    
    
    return RCO.ReturnCode(final_status, msg) 


def get_products_list(options, cfg, logger):
    '''method that gives the product list with their informations from 
       configuration regarding the passed options.
    
    :param options Options: The Options instance that stores the commands 
                            arguments
    :param cfg Config: The global configuration
    :param logger Logger: The logger instance to use for the display and 
                          logging
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
                raise Exception(_("Product %(product)s "
                            "not defined in application %(application)s") %
                        { 'product': p, 'application': cfg.VARS.application} )
    
    # Construct the list of tuple containing 
    # the products name and their definition
    products_infos = src.product.get_products_infos(products, cfg)
    
    products_infos = [pi for pi in products_infos if not(
                                     src.product.product_is_native(pi[1]) or 
                                     src.product.product_is_fixed(pi[1]))]
    
    return products_infos

def log_step(logger, header, step):
    msg = "\r%s%s" % (header, " " * 20)
    msg += "\r%s%s" % (header, step)
    logger.info(msg)
    logger.debug("\n==== %s \n" % UTS.info(step))

def log_res_step(logger, res):
    if res == 0:
        logger.debug("<OK>\n")
    else:
        logger.debug("<KO>\n")


def make_all_products(config, products_infos, make_option, logger):
    '''Execute the proper configuration commands 
       in each product build directory.

    :param config Config: The global configuration
    :param products_info list: List of 
                                 (str, Config) => (product_name, product_info)
    :param make_option str: The options to add to the command
    :param logger Logger: The logger instance to use for the display and logging
    :return: the number of failing commands.
    :rtype: int
    '''
    res = 0
    for p_name_info in products_infos:
        res_prod = make_product(p_name_info, make_option, config, logger)
        if res_prod != 0:
            res += 1 
    return res

def make_product(p_name_info, make_option, config, logger):
    '''Execute the proper configuration command(s) 
       in the product build directory.
    
    :param p_name_info tuple: (str, Config) => (product_name, product_info)
    :param make_option str: The options to add to the command
    :param config Config: The global configuration
    :param logger Logger: The logger instance to use for the display 
                          and logging
    :return: 1 if it fails, else 0.
    :rtype: int
    '''
    
    p_name, p_info = p_name_info
    
    # Logging
    header = _("Make of %s") % UTS.label(p_name)
    header += " %s " % ("." * (20 - len(p_name)))
    logger.info(header)

    # Do nothing if he product is not compilable
    if ("properties" in p_info and \
        "compilation" in p_info.properties and \
        p_info.properties.compilation == "no"):
        log_step(logger, header, "ignored")
        return 0

    # Instantiate the class that manages all the construction commands
    # like cmake, make, make install, make test, environment management, etc...
    builder = src.compilation.Builder(config, logger, p_info)
    
    # Prepare the environment
    log_step(logger, header, "PREPARE ENV")
    res_prepare = builder.prepare()
    log_res_step(logger, res_prepare)
    
    # Execute buildconfigure, configure if the product is autotools
    # Execute cmake if the product is cmake
    len_end_line = 20

    nb_proc, make_opt_without_j = get_nb_proc(p_info, config, make_option)
    log_step(logger, header, "MAKE -j" + str(nb_proc))
    if src.architecture.is_windows():
        res = builder.wmake(nb_proc, make_opt_without_j)
    else:
        res = builder.make(nb_proc, make_opt_without_j)
    log_res_step(logger, res)
    
    # Log the result
    if res > 0:
        logger.info("\r%s%s" % (header, " " * len_end_line))
        logger.info("\r" + header + "<KO>")
        logger.debug("==== <KO> in make of %s\n" % p_name)
    else:
        logger.info("\r%s%s" % (header, " " * len_end_line))
        logger.info("\r" + header + "<OK>")
        logger.debug("==== <OK> in make of %s\n" % p_name)
    logger.info("\n")
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
