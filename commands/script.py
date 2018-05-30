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
  """\
  The script command executes the script(s) of the the given products in the build directory.
  This is done only for the products that are constructed using a script (build_source : 'script').
  Otherwise, nothing is done.

  | Examples:
  |  >> sat script SALOME --products Python,numpy
  """
  
  name = "script"
  
  def getParser(self):
    """Define all options for the command 'sat script <options>'"""
    parser = self.getParserWithHelp()
    parser.add_option('p', 'products', 'list2', 'products',
        _('Optional: products to configure. This option can be'
        ' passed several time to configure several products.'))
    parser.add_option('', 'nb_proc', 'int', 'nb_proc',
        _('Optional: The number of processors to use in the script if the make '
          'command is used in it.\n\tWarning: the script has to be correctly written '
          'if you want this option to work.\n\tThe $MAKE_OPTIONS has to be '
          'used.'), 0)
    return parser

  def run(self, cmd_arguments):
    """method called for command 'sat script <options>'"""
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
    msg = ('Executing the script in the build directories of the application %s') % \
                UTS.label(config.VARS.application)
    logger.info(msg)
    
    info = [(_("BUILD directory"), os.path.join(config.APPLICATION.workdir, 'BUILD'))]
    UTS.logger_info_tuples(logger, info)
    
    # Call the function that will loop over all the products and execute
    # the right command(s)
    if options.nb_proc is None:
        options.nb_proc = 0
    good_result, results = run_script_all_products(config, products_infos, options.nb_proc, logger)
    
    # Print the final state
    nbExpected = len(products_infos)
    msgCount = "(%d/%d)" % (good_result, nbExpected)
    if good_result == nbExpected:
      status = "OK"
      msg = _("Execute script")
      logger.info("\n%s %s: <%s>.\n" % (msg, msgCount, status))
    else:
      status = "KO"
      msg = _("Problem executing script")
      logger.info("\n%s %s: <%s>.\n" % (msg, msgCount, status))

    return RCO.ReturnCode(status, "%s %s" % (msg, msgCount))

def run_script_all_products(config, products_infos, nb_proc, logger):
    """Execute the script in each product build directory.

    :param config: (Config) The global configuration
    :param products_info: (list) 
      List of (str, Config) => (product_name, product_info)
    :param nb_proc: (int) The number of processors to use
    :param logger: (Logger) 
      The logger instance to use for the display and logging
    :return: (int) The number of failing commands.
    """
    # Initialize the variables that will count the fails and success
    results = dict()
    good_result = 0
    DBG.write("run_script_all_products", [p for p, tmp in products_infos])
    for p_name_info in products_infos:
      retcode = run_script_of_product(p_name_info, nb_proc, config, logger)
      # show results
      p_name, p_info = p_name_info
      results[p_name] = retcode
      if retcode.isOk():
        good_result += 1
        
    return good_result, results

def run_script_of_product(p_name_info, nb_proc, config, logger):
    """
    Execute the proper configuration command(s) 
    in the product build directory.
    
    :param p_name_info: (tuple) 
      (str, Config) => (product_name, product_info)
    :param nb_proc: (int) The number of processors to use
    :param config: (Config) The global configuration
    :param logger: (Logger) 
      The logger instance to use for the display and logging
    :return: (int) 1 if it fails, else 0.
    """
    p_name, p_info = p_name_info
    
    header = "zzzz" # TODO
    # Logging
    msg = _("Running script of %s ...") % UTS.label(p_name)
    logger.info(msg)

    # Do nothing if he product is not compilable or has no compilation script
    test1 = "properties" in p_info and \
            "compilation" in p_info.properties and \
            p_info.properties.compilation == "no"
    if ( test1 or (not PROD.product_has_script(p_info)) ):
        UTS.log_step(logger, header, "ignored")
        return res.append(RCO.ReturnCode("OK", "run script %s ignored" % p_name))


    # Instantiate the class that manages all the construction commands
    # like cmake, make, make install, make test, environment management, etc...
    builder = COMP.Builder(config, logger, p_info)
    
    # Prepare the environment
    UTS.log_step(logger, header, "PREPARE ENV ...")
    res_prepare = builder.prepare()
    UTS.log_res_step(logger, res_prepare)
    
    # Execute the script
    script_path_display = UTS.label(p_info.compil_script)
    UTS.log_step(logger, header, "SCRIPT " + script_path_display)
    res = builder.do_script_build(p_info.compil_script, number_of_proc=nb_proc)
    UTS.log_res_step(logger, res)
 
    #logger.info("")

    return res
