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
from src.salomeTools import _BaseCommand

########################################################################
# Command class
########################################################################
class Command(_BaseCommand):
  """\
  The prepare command gets the sources of the application products 
  and apply the patches if there is any.

  examples:
    >> sat prepare SALOME --products KERNEL,GUI
  """
  
  name = "prepare"
  
  def getParser(self):
    """Define all options for command 'sat prepare <options>'"""
    parser = self.getParserWithHelp()
    parser.add_option(
        'p', 'products', 'list2', 'products',
        _('Optional: products to prepare. This option can be'
        ' passed several time to prepare several products.'))
    parser.add_option(
        'f', 'force', 'boolean', 'force', 
        _("Optional: force to prepare the products in development mode."))
    parser.add_option(
        '', 'force_patch', 'boolean', 'force_patch', 
        _("Optional: force to apply patch to the products in development mode."))
    return parser

  def run(self, cmd_arguments):
    """method called for command 'sat prepare <options>'"""
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

    products_infos = self.get_products_list(options, config, logger)

    # Construct the arguments to pass to the clean, source and patch commands
    args_appli = config.VARS.application + ' '
    args_product_opt = '--products '
    if options.products:
        for p_name in options.products:
            args_product_opt += ',' + p_name
    else:
        for p_name, __ in products_infos:
            args_product_opt += ',' + p_name

    ldev_products = [p for p in products_infos if src.product.product_is_dev(p[1])]
    args_product_opt_clean = args_product_opt
    if not options.force and len(ldev_products) > 0:
        l_products_not_getted = find_products_already_getted(ldev_products)
        if len(l_products_not_getted) > 0:
            msg = _("Do not get the source of the following products in development mode\n"
                    "  Use the --force option to overwrite it.\n")
            logger.write(src.printcolors.printcWarning(msg), 1)
            args_product_opt_clean = remove_products(args_product_opt_clean,
                                                     l_products_not_getted,
                                                     logger)
            logger.write("\n", 1)

    
    args_product_opt_patch = args_product_opt
    if not options.force_patch and len(ldev_products) > 0:
        l_products_with_patchs = find_products_with_patchs(ldev_products)
        if len(l_products_with_patchs) > 0:
            msg = _("do not patch the following products in development mode\n"
                    "  Use the --force_patch option to overwrite it.\n")
            logger.write(src.printcolors.printcWarning(msg), 1)
            args_product_opt_patch = remove_products(args_product_opt_patch,
                                                     l_products_with_patchs,
                                                     logger)
            logger.write("\n", 1)

    # Construct the final commands arguments
    args_clean = args_appli + args_product_opt_clean + " --sources"
    args_source = args_appli + args_product_opt  
    args_patch = args_appli + args_product_opt_patch

    # If there is no more any product in the command arguments,
    # do not call the concerned command 
    oExpr = re.compile("^--products *$")
    do_clean = not(oExpr.search(args_product_opt_clean))
    do_source = not(oExpr.search(args_product_opt))
    do_patch = not(oExpr.search(args_product_opt_patch))
    
    
    # Initialize the results to Ok but nothing done status
    res_clean = RCO.ReturnCode("OK", "nothing done")
    res_source = RCO.ReturnCode("OK", "nothing done")
    res_patch = RCO.ReturnCode("OK", "nothing done")

    # return res_clean + res_source + res_patch

    # Call the commands using the API
    if do_clean:
        msg = _("Clean the source directories ...")
        logger.write(msg, 3)
        logger.flush()
        DBG.tofix("args_clean and TODO remove returns", args_clean, True)
        res_clean = runner.getCommand("clean").run(args_clean)
        return res_clean + res_source + res_patch
    if do_source:
        msg = _("Get the sources of the products ...")
        logger.write(msg, 5)
        res_source = runner.getCommand("source").run(args_source)
    if do_patch:
        msg = _("Patch the product sources (if any) ...")
        logger.write(msg, 5)
        res_patch = runner.getCommand("patch").run(args_patch)
    
    return res_clean + res_source + res_patch


def remove_products(arguments, l_products_info, logger):
    '''function that removes the products in l_products_info from arguments list.
    
    :param arguments str: The arguments from which to remove products
    :param l_products_info list: List of 
                                 (str, Config) => (product_name, product_info)
    :param logger Logger: The logger instance to use for the display and logging
    :return: The updated arguments.
    :rtype: str
    '''
    args = arguments
    for i, (product_name, __) in enumerate(l_products_info):
        args = args.replace(',' + product_name, '')
        end_text = ', '
        if i+1 == len(l_products_info):
            end_text = '\n'            
        logger.write(product_name + end_text, 1)
    return args

def find_products_already_getted(l_products):
    '''function that returns the list of products that have an existing source 
       directory.
    
    :param l_products List: The list of products to check
    :return: The list of product configurations that have an existing source 
             directory.
    :rtype: List
    '''
    l_res = []
    for p_name_p_cfg in l_products:
        __, prod_cfg = p_name_p_cfg
        if os.path.exists(prod_cfg.source_dir):
            l_res.append(p_name_p_cfg)
    return l_res

def find_products_with_patchs(l_products):
    '''function that returns the list of products that have one or more patches.
    
    :param l_products List: The list of products to check
    :return: The list of product configurations that have one or more patches.
    :rtype: List
    '''
    l_res = []
    for p_name_p_cfg in l_products:
        __, prod_cfg = p_name_p_cfg
        l_patchs = src.get_cfg_param(prod_cfg, "patches", [])
        if len(l_patchs)>0:
            l_res.append(p_name_p_cfg)
    return l_res
