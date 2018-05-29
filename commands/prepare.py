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
import pprint as PP

import src.debug as DBG
import src.returnCode as RCO
import src.utilsSat as UTS
import src.product as PROD
from src.salomeTools import _BaseCommand

########################################################################
# Command class
########################################################################
class Command(_BaseCommand):
  """
  The prepare command gets the sources of the application products 
  and apply the patches if there is any.

  | examples:
  | >> sat prepare SALOME --products KERNEL,GUI
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

    products_infos = self.get_products_list(options, config)

    # Construct the arguments to pass to the clean, source and patch commands
    args_appli = config.VARS.application
    if options.products:
        listProd = list(options.products)
    else: # no product interpeted as all products
        listProd = [name for name, tmp in products_infos]
        logger.warning("prepare all products:\n%s" % PP.pformat(sorted(listProd)))

    # DBG.write("prepare products", sorted(listProd))
    args_product_opt = '--products ' + ",".join(listProd)
    do_source = (len(listProd) > 0)
    
    ldev_products = [p for p in products_infos if PROD.product_is_dev(p[1])]
    newList = listProd
    if not options.force and len(ldev_products) > 0:
        l_products_not_getted = find_products_already_getted(ldev_products)
        listNot = [i for i, tmp in l_products_not_getted]
        newList, removedList = removeInList(listProd, listNot)
        if len(removedList) > 0:
            msg = _("""\
Do not get the source of the following products in development mode.
Use the --force option to overwrite it.
""")
            logger.error(msg + "\n%s" % ",".join(removedList))
    
    args_product_opt_clean = '--products ' + ",".join(newList)
    do_clean = (len(newList) > 0)
    
    newList = listProd
    if not options.force_patch and len(ldev_products) > 0:
        l_products_with_patchs = find_products_with_patchs(ldev_products)
        listNot = [i for i, tmp in l_products_with_patchs]
        newList, removedList = removeInList(listProd, listNot)
        if len(removedList) > 0:
            msg = _("""
Do not patch the following products in development mode.
Use the --force_patch option to overwrite it.
""")
            logger.error(msg + "\n%s" % ",".join(removedList))
                                                     
    args_product_opt_patch = '--products ' + ",".join(newList)
    do_patch = (len(newList) > 0)
    
    # Construct the final commands arguments
    args_clean = "%s --sources" % args_product_opt_clean
    args_source = "%s" % args_product_opt 
    args_patch = "%s" % args_product_opt_patch
      
    # Initialize the results to Ok but nothing done status
    res_clean = RCO.ReturnCode("OK", "nothing done")
    res_source = RCO.ReturnCode("OK", "nothing done")
    res_patch = RCO.ReturnCode("OK", "nothing done")

    # Call the commands using the API
    # If do_etc there is no more any product in the command arguments
    if do_clean:
        msg = _("Clean the source directories ...")
        logger.info(msg + "(%s)" % args_clean)
        mCmd = self.getMicroCommand("clean", args_appli)
        res_clean = self.runMicroCommand(mCmd, args_clean)
        
    if do_source:
        msg = _("Get the sources of the products ...")
        logger.info(msg + "(%s)" % args_source)
        mCmd = self.getMicroCommand("source", args_appli)
        res_source = self.runMicroCommand(mCmd, args_source)
        
    if do_patch:
        msg = _("Patch the product sources (if any) ...")
        logger.info(msg + "(%s)" % args_patch)
        mCmd = self.getMicroCommand("patch", args_appli)
        res_patch = self.runMicroCommand(mCmd, args_patch)
    
    return res_clean + res_source + res_patch


def removeInList(aList, removeList):
    """Removes elements of removeList list from aList
    
    :param aList: (list) The list from which to remove elements
    :param removeList: (list) The list which contains elements to remove
    :return: (list, list) (list with elements removed, list of elements removed) 
    """
    res1 = [i for i in aList if i not in removeList]
    res2 = [i for i in aList if i in removeList]
    return (res1, res2)


def find_products_already_getted(l_products):
    """Returns the list of products that have an existing source directory.
    
    :param l_products: (list) The list of products to check
    :return: (list) 
      The list of product configurations 
      that have an existing source directory.
    """
    l_res = []
    for p_name_p_cfg in l_products:
        __, prod_cfg = p_name_p_cfg
        if os.path.exists(prod_cfg.source_dir):
            l_res.append(p_name_p_cfg)
    return l_res

def find_products_with_patchs(l_products):
    """Returns the list of products that have one or more patches.
    
    :param l_products: (list) The list of products to check
    :return: (list) 
      The list of product configurations 
      that have one or more patches.
    """
    l_res = []
    for p_name_p_cfg in l_products:
        __, prod_cfg = p_name_p_cfg
        l_patchs = UTS.get_config_key(prod_cfg, "patches", [])
        if len(l_patchs)>0:
            l_res.append(p_name_p_cfg)
    return l_res
