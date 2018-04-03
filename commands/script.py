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
from src.salomeTools import _BaseCommand

########################################################################
# Command class
########################################################################
class Command(_BaseCommand):
  """\
  The script command executes the script(s) of the the given products in the build directory.
  This is done only for the products that are constructed using a script (build_source : 'script').
  Otherwise, nothing is done.

  examples:
    >> sat script SALOME --products Python,numpy
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
    src.check_config_has_application( runner.cfg )

    # Get the list of products to treat
    products_infos = get_products_list(options, runner.cfg, logger)
    
    # Print some informations
    msg = ('Executing the script in the build directories of the application %s\n') % \
                src.printcolors.printcLabel(runner.cfg.VARS.application)
    logger.write(msg, 1)
    
    info = [(_("BUILD directory"), os.path.join(runner.cfg.APPLICATION.workdir, 'BUILD'))]
    src.print_info(logger, info)
    
    # Call the function that will loop over all the products and execute
    # the right command(s)
    if options.nb_proc is None:
        options.nb_proc = 0
    res = run_script_all_products(runner.cfg,
                                  products_infos,
                                  options.nb_proc,
                                  logger)
    
    # Print the final state
    nb_products = len(products_infos)
    if res == 0:
        final_status = "OK"
    else:
        final_status = "KO"
   
    logger.write(_("\nScript: %(status)s (%(1)d/%(2)d)\n") % \
        { 'status': src.printcolors.printc(final_status), 
          '1': nb_products - res,
          '2': nb_products }, 1)    
    
    return res 
    

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
                            "not defined in application %(application)s") % \
                        { 'product': p, 'application': cfg.VARS.application} )
    
    # Construct the list of tuple containing 
    # the products name and their definition
    products_infos = src.product.get_products_infos(products, cfg)
    
    products_infos = [pi for pi in products_infos if not(
                                     src.product.product_is_native(pi[1]) or 
                                     src.product.product_is_fixed(pi[1]))]
    
    return products_infos

def log_step(logger, header, step):
    logger.write("\r%s%s" % (header, " " * 20), 3)
    logger.write("\r%s%s" % (header, step), 3)
    logger.write("\n==== %s \n" % src.printcolors.printcInfo(step), 4)
    logger.flush()

def log_res_step(logger, res):
    if res == 0:
        logger.write("%s \n" % src.printcolors.printcSuccess("OK"), 4)
        logger.flush()
    else:
        logger.write("%s \n" % src.printcolors.printcError("KO"), 4)
        logger.flush()

def run_script_all_products(config, products_infos, nb_proc, logger):
    '''Execute the script in each product build directory.

    :param config Config: The global configuration
    :param products_info list: List of 
                                 (str, Config) => (product_name, product_info)
    :param nb_proc int: The number of processors to use
    :param logger Logger: The logger instance to use for the display and logging
    :return: the number of failing commands.
    :rtype: int
    '''
    res = 0
    for p_name_info in products_infos:
        res_prod = run_script_of_product(p_name_info,
                                      nb_proc,
                                      config,
                                      logger)
        if res_prod != 0:
            res += 1 
    return res

def run_script_of_product(p_name_info, nb_proc, config, logger):
    '''Execute the proper configuration command(s) 
       in the product build directory.
    
    :param p_name_info tuple: (str, Config) => (product_name, product_info)
    :param nb_proc int: The number of processors to use
    :param config Config: The global configuration
    :param logger Logger: The logger instance to use for the display 
                          and logging
    :return: 1 if it fails, else 0.
    :rtype: int
    '''
    
    p_name, p_info = p_name_info
    
    # Logging
    logger.write("\n", 4, False)
    logger.write("################ ", 4)
    header = _("Running script of %s") % src.printcolors.printcLabel(p_name)
    header += " %s " % ("." * (20 - len(p_name)))
    logger.write(header, 3)
    logger.write("\n", 4, False)
    logger.flush()

    # Do nothing if he product is not compilable or has no compilation script
    if ( ("properties" in p_info and 
          "compilation" in p_info.properties and 
          p_info.properties.compilation == "no") or
         (not src.product.product_has_script(p_info)) ):
        log_step(logger, header, "ignored")
        logger.write("\n", 3, False)
        return 0

    # Instantiate the class that manages all the construction commands
    # like cmake, make, make install, make test, environment management, etc...
    builder = src.compilation.Builder(config, logger, p_info)
    
    # Prepare the environment
    log_step(logger, header, "PREPARE ENV")
    res_prepare = builder.prepare()
    log_res_step(logger, res_prepare)
    
    # Execute the script
    len_end_line = 20
    script_path_display = src.printcolors.printcLabel(p_info.compil_script)
    log_step(logger, header, "SCRIPT " + script_path_display)
    len_end_line += len(script_path_display)
    res = builder.do_script_build(p_info.compil_script, number_of_proc=nb_proc)
    log_res_step(logger, res)
    
    # Log the result
    if res > 0:
        logger.write("\r%s%s" % (header, " " * len_end_line), 3)
        logger.write("\r" + header + src.printcolors.printcError("KO"))
        logger.write("==== %(KO)s in script execution of %(name)s \n" % \
            { "name" : p_name , "KO" : src.printcolors.printcInfo("ERROR")}, 4)
        logger.flush()
    else:
        logger.write("\r%s%s" % (header, " " * len_end_line), 3)
        logger.write("\r" + header + src.printcolors.printcSuccess("OK"))
        logger.write("==== %s \n" % src.printcolors.printcInfo("OK"), 4)
        logger.write("==== Script execution of %(name)s %(OK)s \n" % \
            { "name" : p_name , "OK" : src.printcolors.printcInfo("OK")}, 4)
        logger.flush()
    logger.write("\n", 3, False)

    return res
