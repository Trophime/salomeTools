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

  | Examples:
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
    products_infos = self.get_products_list(options, config)
    
    # Print some informations
    msg = _('Executing the check command in the build directories of the application')
    msg = "%s %s" % (msg, UTS.label(config.VARS.application))
    info = [(_("BUILD directory"), os.path.join(config.APPLICATION.workdir, 'BUILD'))]
    msg = "\n" + UTS.formatTuples(info)
    logger.info(msg)
    
    # Call the function that will loop over all the products and execute
    # the right command(s)
    res = self.check_all_products(products_infos)
    
    # Print the final state
    good_result = sum(1 for r in res if r.isOk())
    nbExpected = len(products_infos)
    msgCount = "(%d/%d)" % (good_result, nbExpected)
    if good_result == nbExpected:
      status = "OK"
      msg = _("command check")
      logger.info("\n%s %s: <%s>.\n" % (msg, msgCount, status))
    else:
      status = "KO"
      msg = _("command check, some products have failed")
      logger.info("\n%s %s: <%s>.\n" % (msg, msgCount, status))

    return RCO.ReturnCode(status, "%s %s" % (msg, msgCount))

  def check_all_products(self, products_infos):
    """
    Execute the proper configuration commands 
    in each product build directory.

    :param products_info: (list) 
      List of (str, Config) => (product_name, product_info)
    :return: (list of RCO.ReturnCode) list of OK if it succeed
    """
    res = []
    for p_name_info in products_infos:
      res.append(self.check_product(p_name_info)
    return res

  def check_product(self, p_name_info):
    """
    Execute the proper configuration command(s) 
    in the product build directory.
    
    :param p_name_info: (tuple) 
      (str, Config) => (product_name, product_info)
    :return: (RCO.ReturnCode)
    """
    # shortcuts
    runner = self.getRunner()
    config = self.getConfig()
    logger = self.getLogger()
    options = self.getOptions()
    
    p_name, p_info = p_name_info

    header = _("Check of %s") % UTS.label(p_name)
    UTS.init_log_step(logger,header)

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
        UTS.log_step(logger, "ignored")
        if not cmd_found:
            return RCO.ReturnCode("KO", "command not found product %s" % p_name)
        return RCO.ReturnCode("OK", "ignored product %s" % p_name)
    
    # Instantiate the class that manages all the construction commands
    # like cmake, check, make install, make test, environment management, etc...
    builder = COMP.Builder(config, logger, p_info)
    
    # Prepare the environment
    UTS.log_step(logger, "PREPARE ENV")
    res_prepare = builder.prepare()
    UTS.log_step(logger, res_prepare)

    # Launch the check    
    UTS.log_step(logger, "CHECK")
    res = builder.check(command=command)
    UTS.log_step(logger, res)

    return res

