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


import os
import src.debug as DBG
import src.returnCode as RCO
import src.utilsSat as UTS
import src.pyconf as PYCONF
import src.product as PROD
from src.salomeTools import _BaseCommand


########################################################################
# Command class
########################################################################
class Command(_BaseCommand):
  """
  The compile command constructs the products of the application
  
  | Examples:
  | >> sat compile SALOME --products KERNEL,GUI,MEDCOUPLING --clean_all
  """
  
  name = "compile"
  
  def getParser(self):
    """Define all options for the command 'sat compile <options>'"""
    parser = self.getParserWithHelp()
    parser.add_option(
        'p', 'products', 'list2', 'products',
        _('Optional: products to configure. This option can be passed several time to configure several products.'))
    parser.add_option(
        '', 'with_fathers', 'boolean', 'fathers',
        _("Optional: build all necessary products to the given product (KERNEL is build before building GUI)."), 
        False)
    parser.add_option(
        '', 'with_children', 'boolean', 'children',
        _("Optional: build all products using the given product (all SMESH plugins  are build after SMESH)."),
        False)
    parser.add_option(
        '', 'clean_all', 'boolean', 'clean_all',
        _("Optional: clean BUILD dir and INSTALL dir before building product."),
        False)
    parser.add_option(
        '', 'clean_install', 'boolean', 'clean_install',
        _("Optional: clean INSTALL dir before building product."), False)
    parser.add_option(
        '', 'make_flags', 'string', 'makeflags',
        _("Optional: add extra options to the 'make' command."))
    parser.add_option(
        '', 'show', 'boolean', 'no_compile',
        _("Optional: DO NOT COMPILE just show if products are installed or not."),
        False)
    parser.add_option(
        '', 'stop_first_fail', 'boolean', 'stop_first_fail', _(
        "Optional: Stops the command at first product compilation fail."), 
        False)
    parser.add_option(
        '', 'check', 'boolean', 'check', 
        _("Optional: execute the unit tests after compilation"), 
       False)
    parser.add_option(
        '', 'clean_build_after', 'boolean', 'clean_build_after', 
        _('Optional: remove the build directory after successful compilation'), 
        False)
    return parser

  def run(self, cmd_arguments):
    """method called for command 'sat compile <options>'"""
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

    # Warn the user if he invoked the clean_all option 
    # without --products option

    if (options.clean_all and options.products is None):
      msg = _("You used --clean_all without specifying a product, erasing all.")
      if runner.getAnswer(msg) == "NO":
        return RCO.ReturnCode("OK", "user do not want to continue")
      runner.setConfirmMode(False) # user agree for all next
              
    # check that the command has been called with an application
    UTS.check_config_has_application(config).raiseIfKo()

    # Print some informations
    nameApp = str(config.VARS.application)
    srcDir = os.path.join(config.APPLICATION.workdir, 'SOURCES')
    buildDir = os.path.join(config.APPLICATION.workdir, 'BUILD')
    
    msg = _("Application %s, executing compile commands in build directories of products.") % \
            UTS.label(nameApp)
    info = [ (_("SOURCE directory"), UTS.info(srcDir)),
             (_("BUILD directory"), UTS.info(buildDir)) ]    
    msg += "\n" + UTS.formatTuples(info)
    logger.info(msg)

    # Get the list of products to treat
    products_infos = self.get_products_list(options, config)

    if options.fathers:
        # Extend the list with all recursive dependencies of the given products
        products_infos = extend_with_fathers(config, products_infos)

    if options.children:
        # Extend the list with all products that use the given products
        products_infos = extend_with_children(config, products_infos)

    # Sort the list regarding the dependencies of the products
    products_infos = sort_products(config, products_infos)
    
    # Call the function that will loop over all the products and execute
    # the right command(s)
    res = self.compile_all_products(products_infos)
    
    # Print the final state
    nb_products = len(products_infos)
    nb_ok = res.getValue()
      
    logger.info(_("\nCompilation: <%(0)s> (%(1)d/%(2)d)\n") % \
        { '0': res.getStatus(), 
          '1': nb_ok,
          '2': nb_products } )    
    return res


  def compile_all_products(self, products_infos): #sat, config, options, products_infos, logger):
    """
    Execute the proper configuration commands 
    in each product build directory.

    :param config: (Config) The global configuration
    :param products_info: (list)
      List of (str, Config) => (product_name, product_info)
    :param logger: (Logger) 
      The logger instance to use for the display and logging
    :return: (RCO.ReturnCode) with value as the number of failing commands.
    """
    # shortcuts
    config = self.getConfig()
    options = self.getOptions()
    logger = self.getLogger()
    nameAppli = config.VARS.application
    
    res = [] # list of results for each products
    DBG.write("compile", [p for p, tmp in products_infos])
    header = None
    for p_name_info in products_infos:
        
        p_name, p_info = p_name_info
        
        if header is not None: # close previous step in for loop
          UTS.end_log_step(logger, res[-1])
          
        # Logging
        header = _("Compilation of %s ...") % UTS.label(p_name)
        UTS.init_log_step(logger, header)
        
        # Do nothing if the product is not compilable
        if ("properties" in p_info and \
            "compilation" in p_info.properties and \
            p_info.properties.compilation == "no"):     
            UTS.log_step(logger, "ignored")
            res.append(RCO.ReturnCode("OK", "compile %s ignored" % p_name))
            continue

        # Do nothing if the product is native
        if PROD.product_is_native(p_info):
            UTS.log_step(logger, "native")
            res.append(RCO.ReturnCode("OK", "no compile %s as native" % p_name))
            continue

        # Clean the build and the install directories 
        # if the corresponding options was called
        if options.clean_all:
            UTS.log_step(logger, "CLEAN BUILD AND INSTALL")
            # import time 
            # time.sleep(5)
            # UTS.log_step(logger, header, "IIYOO")
            # raise Exception('YOO')    
            cmd_args = "--products %s --build --install" % p_name
            rc = self.executeMicroCommand("clean", nameAppli, cmd_args)
            if not rc.isOk():
              res.append(rc)
              continue
        
        # Clean the the install directory 
        # if the corresponding option was called
        if options.clean_install and not options.clean_all:
            UTS.log_step(logger, "CLEAN INSTALL")
            cmd_args = "--products %s --install" % p_name
            rc = self.executeMicroCommand("clean", nameAppli, cmd_args)
            if not rc.isOk():
              res.append(rc)
              continue
        
        # Recompute the product information to get the right install_dir
        # (it could change if there is a clean of the install directory)
        p_info = PROD.get_product_config(config, p_name)
        
        # Check if it was already successfully installed
        if PROD.check_installation(p_info):
            UTS.log_step(logger, _("already installed"))
            res.append(RCO.ReturnCode("OK", "no compile %s as already installed" % p_name))
            continue
        
        # If the show option was called, do not launch the compilation
        if options.no_compile:
            UTS.log_step(logger, _("No compile and install as show option"))
            res.append(RCO.ReturnCode("OK", "no compile %s as show option" % p_name))
            continue
        
        # Check if the dependencies are installed
        l_depends_not_installed = check_dependencies(config, p_name_info)
        if len(l_depends_not_installed) > 0:
            UTS.log_step(logger, "<KO>")
            msg = _("the following products are mandatory:\n")
            for prod_name in sorted(l_depends_not_installed):
                msg += "%s\n" % prod_name
            logger.error(msg)
            res.append(RCO.ReturnCode("KO", "no compile %s as missing mandatory product(s)" % p_name))
            continue
        
        # Call the function to compile the product
        rc = self.compile_product(p_name_info)
        error_step, nameprod, install_dir = rc.getValue()
        res.append(rc)
        
        if not rc.isOk(): 
          # problem
          if error_step != "CHECK":
            # Clean the install directory if there is any
            logger.debug(_("Cleaning the install directory if there is any"))
            cmd_args = "--products %s --install" % p_name
            rc0 = self.executeMicroCommand("clean", nameAppli, cmd_args)       
        else: 
          # Ok Clean the build directory if the compilation and tests succeed
          if options.clean_build_after:
            UTS.log_step(logger, "CLEAN BUILD")
            cmd_args = "--products %s --build" % p_name
            rc0 = self.executeMicroCommand("clean", nameAppli, cmd_args)

        
        if not rc.isOk() and options.stop_first_fail:
          logger.warning("Stop on first fail option activated")
          break # stop at first problem
          
        
    if header is not None: # close last step in for loop
      UTS.end_log_step(logger, res[-1])
    
    resAll = RCO.ReturnCodeFromList(res)
    nbOk = len([r for r in res if r.isOk()])
    nbKo = len([r for r in res if not r.isOk()])
    if resAll.isOk(): # no failing commands
      return RCO.ReturnCode("OK", "No failing compile commands", nbOk)
    else:
      return RCO.ReturnCode("KO", "Existing %s failing compile product(s)" % nbKo, nbOk)

  def compile_product(self, p_name_info):
    """
    Execute the proper configuration command(s) 
    in the product build directory.
    
    :param p_name_info: (tuple) (str, Config) => (product_name, product_info)
    :return: (RCO.ReturnCode) KO if it fails.
    """
    config = self.getConfig()
    options = self.getOptions()
    logger = self.getLogger()
    
    nameAppli = config.VARS.application
    p_name, p_info = p_name_info
          
    # Get the build procedure from the product configuration.
    # It can be :
    # build_sources : autotools -> build_configure, configure, make, make install
    # build_sources : cmake     -> cmake, make, make install
    # build_sources : script    -> script executions
    if (PROD.product_is_autotools(p_info) or PROD.product_is_cmake(p_info)):
        rc = self.compile_product_cmake_autotools(p_name_info)

    if PROD.product_has_script(p_info):
        rc = self.compile_product_script(p_name_info)

    # Check that the install directory exists
    if rc.isOk() and not(os.path.exists(p_info.install_dir)):
        error_step = "NO INSTALL DIR"
        msg = _("All steps ended successfully, but install directory not found")
        logger.error(msg)
        return RCO.ReturnCode("KO", "Install directory for %s not found" % p_name, (error_step, p_name, p_info.install_dir))
    
    # Add the config file corresponding to the dependencies/versions of the 
    # product that have been successfully compiled
    if rc.isOk():       
        logger.debug(_("Add the config file in installation directory"))
        add_compile_config_file(p_info, config)
        
        if options.check:
            # Do the unit tests (call the check command)
            UTS.log_step(logger, "CHECK")
            cmd_args = "--products %s" % p_name
            rc0 = self.executeMicroCommand("check", nameAppli, cmd_args)
            if not rc0.isOk():
                error_step = "CHECK"
                msg = _("compile steps ended successfully, but check problem")
                logger.error(msg)
                return RCO.ReturnCode("KO", "check of compile for %s problem" % p_name, (error_step, p_name, p_info.install_dir))
    
    rc.setValue( ("COMPILE", p_name, p_info.install_dir) )
    return rc

  def compile_product_cmake_autotools(self, p_name_info):
    """
    Execute the proper build procedure for autotools or cmake
    in the product build directory.
    
    :param p_name_info: (tuple) 
      (str, Config) => (product_name, product_info)
    :return: (RCO.ReturnCode) KO if it fails.
    """
    config = self.getConfig()
    options = self.getOptions()
    logger = self.getLogger()
    
    nameAppli = config.VARS.application
    p_name, p_info = p_name_info
    
    # Execute "sat configure", "sat make" and "sat install"
    res = []
    error_step = ""
    
    # Logging and sat command call for configure step
    UTS.log_step(logger, "CONFIGURE")
    cmd_args = "--products %s" % p_name
    rc = self.executeMicroCommand("configure", nameAppli, cmd_args)
    if not rc.isOk():
      error_step = "CONFIGURE"
      msg = _("sat configure problem")
      logger.error(msg)
      return RCO.ReturnCode("KO", "sat configure %s problem" % p_name, (error_step, p_name, p_info.install_dir))
      
    res.append(rc)
    
    # Logging and sat command call for make step
    # Logging take account of the fact that the product has a compilation script or not
    if PROD.product_has_script(p_info):
      # if the product has a compilation script, 
      # it is executed during make step
      script_path_display = UTS.label(p_info.compil_script)
      UTS.log_step(logger, "SCRIPT " + script_path_display)
    else:
      UTS.log_step(logger, "MAKE")
    
    cmd_args = "--products %s" % p_name
    # Get the make_flags option if there is any
    if options.makeflags:
        cmd_args += " --option -j%s" % options.makeflags
    rc = self.executeMicroCommand("make", nameAppli, cmd_args)
    if not rc.isOk():
      error_step = "MAKE"
      msg = _("sat make problem")
      logger.error(msg)
      return RCO.ReturnCode("KO", "sat make %s problem" % p_name, (error_step, p_name, p_info.install_dir))
    
    res.append(rc)
    
    # Logging and sat command call for make install step
    UTS.log_step(logger, "MAKE INSTALL")
    cmd_args = "--products %s" % p_name
    rc = self.executeMicroCommand("makeinstall", nameAppli, cmd_args)
    if not rc.isOk():
      error_step = "MAKEINSTALL"
      msg = _("sat makeinstall problem")
      logger.error(msg)
      return RCO.ReturnCode("KO", "sat makeinstall %s problem" % p_name, (error_step, p_name, p_info.install_dir))
    
    return RCO.ReturnCode("OK", "compile cmake autotools %s done" % p_name)

  def compile_product_script(self, p_name_info):
    """Execute the script build procedure in the product build directory.
    
    :param p_name_info: (tuple) 
      (str, Config) => (product_name, product_info)
    :return: (RCO.ReturnCode) KO if it fails.
    """
    config = self.getConfig()
    options = self.getOptions()
    logger = self.getLogger()
    nameAppli = config.VARS.application
    
    p_name, p_info = p_name_info
    
    # Execute "sat configure", "sat make" and "sat install"
    error_step = ""
    
    # Logging and sat command call for the script step
    script_path_display = UTS.label(p_info.compil_script)
    UTS.log_step(logger, "SCRIPT %s ..." % script_path_display)
    
    # res = sat.script(config.VARS.application + " --products " + p_name, verbose = 0, logger_add_link = logger)
    cmd_args = "--products %s" % p_name
    res = self.executeMicroCommand("script", nameAppli, cmd_args)
    UTS.log_step(logger, res)
    return res
    
    
def get_children(config, p_name_p_info):
    l_res = []
    p_name, __ = p_name_p_info
    # Get all products of the application
    products = config.APPLICATION.products
    products_infos = PROD.get_products_infos(products, config)
    for p_name_potential_child, p_info_potential_child in products_infos:
        if ("depend" in p_info_potential_child and \
            p_name in p_info_potential_child.depend):
            l_res.append(p_name_potential_child)
    return l_res

def get_recursive_children(config, p_name_p_info, without_native_fixed=False):
    """
    Get the recursive list of the product that depend on 
    the product defined by prod_info
    
    :param config: (Config) The global configuration
    :param prod_info: (Config) The specific config of the product
    :param without_native_fixed: (bool) 
      If true, do not include the fixed or native products in the result
    :return: (list) The list of product_informations.
    """
    p_name, __ = p_name_p_info
    # Initialization of the resulting list
    l_children = []
    
    # Get the direct children (not recursive)
    l_direct_children = get_children(config, p_name_p_info)
    # Minimal case : no child
    if l_direct_children == []:
        return []
    # Add the children and call the function to get the children of the
    # children
    for child_name in l_direct_children:
        l_children_name = [pn_pi[0] for pn_pi in l_children]
        if child_name not in l_children_name:
            if child_name not in config.APPLICATION.products:
                msg = _("""\
The product %(child_name)s that is in %(product_name)s children
is not present in application %(appli_name)s.""" % 
                     {"child_name" : child_name, 
                      "product_name" : p_name.name, 
                      "appli_name" : config.VARS.application} )
                raise Exception(msg)
            prod_info_child = PROD.get_product_config(config, child_name)
            pname_pinfo_child = (prod_info_child.name, prod_info_child)
            # Do not append the child if it is native or fixed and 
            # the corresponding parameter is called
            if without_native_fixed:
                if not(PROD.product_is_native(prod_info_child) or \
                   PROD.product_is_fixed(prod_info_child)):
                    l_children.append(pname_pinfo_child)
            else:
                l_children.append(pname_pinfo_child)
            # Get the children of the children
            l_grand_children = get_recursive_children(config,
                                pname_pinfo_child,
                                without_native_fixed = without_native_fixed)
            l_children += l_grand_children
    return l_children

def get_recursive_fathers(config, p_name_p_info, without_native_fixed=False):
    """
    Get the recursive list of the dependencies of the product defined 
    by prod_info
    
    :param config: (Config) The global configuration
    :param prod_info: (Config) The specific config of the product
    :param without_native_fixed: (bool) 
      If true, do not include the fixed or native products in the result
    :return: (list) The list of product_informations.
    """
    p_name, p_info = p_name_p_info
    # Initialization of the resulting list
    l_fathers = []
    # Minimal case : no dependencies
    if "depend" not in p_info or p_info.depend == []:
        return []
    # Add the dependencies and call the function to get the dependencies of the
    # dependencies
    for father_name in p_info.depend:
        l_fathers_name = [pn_pi[0] for pn_pi in l_fathers]
        if father_name not in l_fathers_name:
            if father_name not in config.APPLICATION.products:
                msg = _("The product %(father_name)s that is in %(product_nam"
                        "e)s dependencies is not present in application %(appli_name)s" % \
                        {"father_name" : father_name, 
                         "product_name" : p_name, 
                         "appli_name" : config.VARS.application})
                raise Exception(msg)
            prod_info_father = PROD.get_product_config(config, father_name)
            pname_pinfo_father = (prod_info_father.name, prod_info_father)
            # Do not append the father if it is native or fixed and 
            # the corresponding parameter is called
            if without_native_fixed:
                if not(PROD.product_is_native(prod_info_father) or \
                   PROD.product_is_fixed(prod_info_father)):
                    l_fathers.append(pname_pinfo_father)
            else:
                l_fathers.append(pname_pinfo_father)
            # Get the dependencies of the dependency
            l_grand_fathers = get_recursive_fathers(config,
                                pname_pinfo_father,
                                without_native_fixed = without_native_fixed)
            for item in l_grand_fathers:
                if item not in l_fathers:
                    l_fathers.append(item)
    return l_fathers

def sort_products(config, p_infos):
    """Sort the p_infos regarding the dependencies between the products
    
    :param config: (Config) The global configuration
    :param p_infos: (list) 
      List of (str, Config) => (product_name, product_info)
    """
    l_prod_sorted = UTS.deepcopy_list(p_infos)
    for prod in p_infos:
        l_fathers = get_recursive_fathers(config,
                                          prod,
                                          without_native_fixed=True)
        l_fathers = [father for father in l_fathers if father in p_infos]
        if l_fathers == []:
            continue
        for p_sorted in l_prod_sorted:
            if p_sorted in l_fathers:
                l_fathers.remove(p_sorted)
            if l_fathers==[]:
                l_prod_sorted.remove(prod)
                l_prod_sorted.insert(l_prod_sorted.index(p_sorted)+1, prod)
                break
        
    return l_prod_sorted

def extend_with_fathers(config, p_infos):
    p_infos_res = UTS.deepcopy_list(p_infos)
    for p_name_p_info in p_infos:
        fathers = get_recursive_fathers(config,
                                        p_name_p_info,
                                        without_native_fixed=True)
        for p_name_p_info_father in fathers:
            if p_name_p_info_father not in p_infos_res:
                p_infos_res.append(p_name_p_info_father)
    return p_infos_res

def extend_with_children(config, p_infos):
    p_infos_res = UTS.deepcopy_list(p_infos)
    for p_name_p_info in p_infos:
        children = get_recursive_children(config,
                                        p_name_p_info,
                                        without_native_fixed=True)
        for p_name_p_info_child in children:
            if p_name_p_info_child not in p_infos_res:
                p_infos_res.append(p_name_p_info_child)
    return p_infos_res    

def check_dependencies(config, p_name_p_info):
    l_depends_not_installed = []
    fathers = get_recursive_fathers(config, p_name_p_info, without_native_fixed=True)
    for p_name_father, p_info_father in fathers:
        if not(PROD.check_installation(p_info_father)):
            l_depends_not_installed.append(p_name_father)
    return l_depends_not_installed


def add_compile_config_file(p_info, config):
    """
    Execute the proper configuration command(s) 
    in the product build directory.
    
    :param p_info: (Config) The specific config of the product
    :param config: (Config) The global configuration
    """
    # Create the compile config
    compile_cfg = PYCONF.Config()
    for prod_name in p_info.depend:
        if prod_name not in compile_cfg:
            compile_cfg.addMapping(prod_name, PYCONF.Mapping(compile_cfg), "")
        prod_dep_info = PROD.get_product_config(config, prod_name, False)
        compile_cfg[prod_name] = prod_dep_info.version
    # Write it in the install directory of the product
    compile_cfg_path = os.path.join(p_info.install_dir, UTS.get_CONFIG_FILENAME())
    with open(compile_cfg_path, 'w') as f:
      compile_cfg.__save__(f)
    
