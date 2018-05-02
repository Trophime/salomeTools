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
import subprocess

import src.debug as DBG
import src.returnCode as RCO
import src.utilsSat as UTS
from src.salomeTools import _BaseCommand
import commands.prepare

########################################################################
# Command class
########################################################################
class Command(_BaseCommand):
  """
  The patch command apply the patches on the sources of the application products
  if there is any.

  | examples:
  | >> sat patch SALOME --products qt,boost
  """
  
  name = "patch"
  
  def getParser(self):
    """Define all options for command 'sat patch <options>'"""
    parser = self.getParserWithHelp()
    parser.add_option('p', 'products', 'list2', 'products',
        _('Optional: products to get the sources. This option can be'
        ' passed several time to get the sources of several products.'))
    return parser

  def run(self, cmd_arguments):
    """method called for command 'sat patch <options>'"""
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

    # Print some informations
    logger.info("Patching sources of the application %s\n" % \
                UTS.blue(config.VARS.application))

    logger.info('  workdir = %s\n\n"', UTS.blue(config.APPLICATION.workdir))

    # Get the products list with products informations regarding the options
    products_infos = commands.prepare.get_products_list(options, config, logger)
    
    # Get the maximum name length in order to format the terminal display
    max_product_name_len = 1
    if len(products_infos) > 0:
        max_product_name_len = max(map(lambda l: len(l), products_infos[0])) + 4
    
    # The loop on all the products on which to apply the patches
    good_result = 0
    for __, product_info in products_infos:
        # Apply the patch
        return_code, patch_res = apply_patch(config,
                                             product_info,
                                             max_product_name_len,
                                             logger)
        logger.info(patch_res)
        if return_code:
            good_result += 1
    
    # Display the results (how much passed, how much failed, etc...)

    logger.info("\n")
    if good_result == len(products_infos):
        status = "OK"
    else:
        status = "KO"
    
    # write results
    msg = ("\nPatching sources of the application: <%s> (%d/%d)\n") % \
                  (status, good_result, len(products_infos))
    logger.info(msg)    

    return RCO.ReturnCode(status, msg)
     

def apply_patch(config, product_info, max_product_name_len, logger):
    """The method called to apply patches on a product

    :param config: (Config) The global configuration
    :param product_info: (Config) 
      The configuration specific to the product to be patched
    :param logger: (Logger: 
      The logger instance to use for the display and logging
    :return: (RCO.ReturnCode)
    """

    # if the product is native, do not apply patch
    if src.product.product_is_native(product_info):
        # display and log
        logger.info('%s: ' % UTS.label(product_info.name))
        logger.info(' ' * (max_product_name_len - len(product_info.name)))
        logger.info("\n")
        msg = _("The %s product is native. Do not apply any patch") % product_info.name
        logger.info(msg + "\n")
        return RCO.ReturnCode("OK", msg)     

    if not "patches" in product_info or len(product_info.patches) == 0:
        # display and log
        logger.info('%s: ' % UTS.label(product_info.name))
        logger.info(' ' * (max_product_name_len - len(product_info.name)))
        logger.info("\n")
        msg = _("No patch for the %s product") % product_info.name
        logger.info(msg + "\n")
        return RCO.ReturnCode("OK", msg) 
    else:
        # display and log
        logger.info('%s: ' % UTS.label(product_info.name))
        logger.info(' ' * (max_product_name_len - len(product_info.name)))
        logger.info("\n")

    if not os.path.exists(product_info.source_dir):
        msg = _("No sources found for the %s product") % product_info.name
        logger.error(UTS.red(msg))
        return RCO.ReturnCode("KO", msg)

    # At this point, there one or more patches and the source directory exists
    retcode = []
    res = []
    # Loop on all the patches of the product
    for patch in product_info.patches:
        details = []
        
        # Check the existence and apply the patch
        if os.path.isfile(patch):
            patch_cmd = "patch -p1 < %s" % patch
            
            # Write the command in the terminal if verbose level is at 5
            logger.info("    >%s\n" % patch_cmd)
            
            # Write the command in the log file (can be seen using 'sat log')
            logger.logTxtFile.write("\n    >%s\n" % patch_cmd)
            logger.logTxtFile.flush()
            
            # Call the command
            res_cmd = subprocess.call(
                         patch_cmd, 
                         shell=True, 
                         cwd=product_info.source_dir,
                         stdout=logger.logTxtFile, 
                         stderr=subprocess.STDOUT )
                         
            res_cmd = (res_cmd == 0)       
        else:
            res_cmd = False
            details.append("  " + UTS.red(_("Not a valid patch: %s\n")) % patch)

        res.append(res_cmd)
        
        if res_cmd:
            message = _("Apply patch %s") % UTS.blue(patch)
        else:
            message = _("Failed to apply patch %s") % UTS.red(patch)

        if config.USER.output_verbose_level >= 3:
            retcode.append("  %s" % message)
        else:
            retcode.append("%s: %s" % (product_info.name, message))
        
        if len(details) > 0:
            retcode.extend(details)

    if False in res: 
      rc = "KO"
    else:
      rc = "OK"
    
    return RCO.ReturnCode(rc, "\n".join(retcode))
