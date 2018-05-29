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

import subprocess as SP

import src.debug as DBG
import src.returnCode as RCO
import src.utilsSat as UTS
import src.product as PROD
import src.compilation as COMP
from src.salomeTools import _BaseCommand
import src.pyconf as PYCONF
import src.environment as ENVI

########################################################################
# Command class
########################################################################
class Command(_BaseCommand):
  """
  The generate command generates SALOME modules from 'pure cpp' products.

  | warning: this command NEEDS YACSGEN to run.
  | 
  | Examples:
  | >> sat generate SALOME --products FLICACPP
  """
  
  name = "generate"
  
  def getParser(self):
    """Define all options for command 'sat generate <options>'"""
    parser = self.getParserWithHelp()
    parser.add_option('p', 'products', 'list2', 'products',
                      _("Optional: the list of products to generate"))
    parser.add_option('', 'yacsgen', 'string', 'yacsgen',
                      _("Optional: path to YACSGEN's module_generator package"))
    return parser
  
  def run(self, cmd_arguments):
    """method called for command 'sat generate <options>'"""
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
    
    # Check that the command has been called with an application
    UTS.check_config_has_application(config).raiseIfKo()
    
    logger.info( _('Generation of SALOME modules for application %s\n') % \
        UTS.label(config.VARS.application) )

    status = RCO._KO_STATUS

    # verify that YACSGEN is available
    returnCode = check_yacsgen(config, options.yacsgen, logger)
    
    if not returnCode.isOk():
        logger.error(returnCode.getWhy())
        return returnCode
    else:
        yacsgen_dir = returnCode.getValue()
        
    # Make the generator module visible by python
    sys.path.insert(0, yacsgen_dir)
    
    logger.info(" insert directory PATH %s = %s\n" % \
                ("YACSGEN", UTS.blue(yacsgen_dir)) )

    products = config.APPLICATION.products
    if options.products:
        products = options.products

    details = []
    nbgen = 0

    context = build_context(config, logger)
    lprod = UTS.label(product)
    for product in products:
        header = _("Generating %s") % lprod
        header += " %s " % ("." * (20 - len(product)))
        logger.info(header)

        if product not in config.PRODUCTS:
            logger.error(_("Unknown product %s") % lprod)
            continue

        pi = PROD.get_product_config(config, product)
        if not PROD.product_is_generated(pi):
            logger.info(_("not a generated product %s") % lprod)
            continue

        nbgen += 1
        try:
            result = generate_component_list(config, pi, context, logger)
        except Exception as exc:
            result = str(exc)

        if result != RCO._OK_STATUS:
            details.append([product, result])

    if len(details) != 0:
        msg = _("The following modules were not generated correctly:\n")
        for d in details:
          msg += "  %s: %s\n" % (d[0], d[1])
        logger.error(msg)
        return RCO.ReturnCode("KO", msg)
    else:
        return RCO.ReturnCode("OK", "generate command done")


def generate_component_list(config, product_info, context, logger):
    res = "?"
    logger.info("\n")
    for compo in PROD.get_product_components(product_info):
        header = "  %s %s " % (UTS.label(compo), "." * (20 - len(compo)))
        res = generate_component(config, compo, product_info, context, header, logger)
        logger.info("\r%s%s\r%s" % (header, " " * 20, header))
        logger.info(res + "\n")
    return res

def generate_component(config, compo, product_info, context, header, logger):
    """get from config include file name and librairy name, or take default value"""
    if "hxxfile" in product_info:
        hxxfile = product_info.hxxfile
    else:
        hxxfile = compo + ".hxx"
    if "cpplib" in product_info:
        cpplib = product_info.cpplib
    else:
        cpplib = "lib" + compo + "CXX.so"
    cpp_path = product_info.install_dir

    msg = ""
    msg += "%s\n" % UTS.blue(header)
    msg += "hxxfile  = %s\n" % hxxfile
    msg += "cpplib   = %s\n" % cpplib
    msg += "cpp_path = %s\n" % cpp_path
    logger.debug(msg)
    
    # create a product_info at runtime
    compo_info = PYCONF.Mapping(config)
    compo_info.name = compo
    compo_info.nb_proc = 1
    generate_dir = os.path.join(config.APPLICATION.workdir, "GENERATED")
    install_dir = os.path.join(config.APPLICATION.workdir, "INSTALL")
    build_dir = os.path.join(config.APPLICATION.workdir, "BUILD")
    compo_info.source_dir = os.path.join(generate_dir, compo + "_SRC")
    compo_info.install_dir = os.path.join(install_dir, compo)
    compo_info.build_dir = os.path.join(build_dir, compo)
    compo_info.depend = product_info.depend
    compo_info.depend.append(product_info.name, "") # add cpp module
    compo_info.opt_depend = product_info.opt_depend

    config.PRODUCTS.addMapping(compo, PYCONF.Mapping(config), "")
    config.PRODUCTS[compo].default = compo_info

    builder = COMP.Builder(config, logger, compo_info, check_src=False)
    builder.header = header

    # generate the component
    # create GENERATE dir if necessary
    if not os.path.exists(generate_dir):
        os.mkdir(generate_dir)

    # delete previous generated directory if it already exists
    if os.path.exists(compo_info.source_dir):
        logger.debug("  delete %s" % compo_info.source_dir)
        shutil.rmtree(compo_info.source_dir)

    # generate generates in the current directory => change for generate dir
    curdir = os.curdir
    os.chdir(generate_dir)

    # inline class to override bootstrap method
    import module_generator
    
    class sat_generator(module_generator.Generator):
        # old bootstrap for automake (used if salome version <= 7.4)
        def bootstrap(self, source_dir, log_file):
            # replace call to default bootstrap() by using subprocess call (cleaner)
            command = "sh autogen.sh"
            ier = SP.call(command, shell=True, cwd=source_dir, stdout=log_file, stderr=SP.STDOUT)
            if ier != 0:
                raise Exception("bootstrap has ended in error")

    
    # determine salome version
    VersionSalome = UTS.get_salome_version(config)
    if VersionSalome >= 750 :
        use_autotools=False
        logger.info('USE CMAKE')
    else:
        use_autotools=True
        logger.info('USE AUTOTOOLS')

    result = "GENERATE"
    logger.info('GENERATE')
    
    prevstdout = sys.stdout
    prevstderr = sys.stderr

    try:
        sys.stdout = logger.logTxtFile
        sys.stderr = logger.logTxtFile

        if PROD.product_is_mpi(product_info):
            salome_compo = module_generator.HXX2SALOMEParaComponent(hxxfile,
                                                                    cpplib,
                                                                    cpp_path)
        else:
            salome_compo = module_generator.HXX2SALOMEComponent(hxxfile,
                                                                cpplib,
                                                                cpp_path)

        if PROD.product_has_salome_gui(product_info):
            # get files to build a template GUI
            gui_files = salome_compo.getGUIfilesTemplate(compo)
        else:
            gui_files = None

        mg = module_generator.Module(compo, components=[salome_compo],
                                     prefix=generate_dir, gui=gui_files)
        g = sat_generator(mg, context)
        g.generate()

        if use_autotools:
            result = "BUID_CONFIGURE"
            logger.info('BUID_CONFIGURE (no bootstrap)')
            g.bootstrap(compo_info.source_dir, logger.logTxtFile)

        result = RCO._OK_STATUS
    finally:
        sys.stdout = prevstdout
        sys.stderr = prevstderr

    # go back to previous directory
    os.chdir(curdir)

    # do the compilation using the builder object
    if builder.prepare()!= 0: return "Error in prepare"
    if use_autotools:
        if builder.configure()!= 0: return "Error in configure"
    else:
        if builder.cmake()!= 0: return "Error in cmake"

    if builder.make(config.VARS.nb_proc, "")!=0: return "Error in make"
    if builder.install()!=0: return "Error in make install"

    # copy specified logo in generated component install directory
    # rem : logo is not copied in source dir because this would require
    #       to modify the generated makefile
    logo_path = PROD.product_has_logo(product_info)
    if logo_path:
        destlogo = os.path.join(compo_info.install_dir, "share", "salome",
            "resources", compo.lower(), compo + ".png")
        UTS.Path(logo_path).copyfile(destlogo)

    return result

def build_context(config, logger):
    products_list = [ 'KERNEL', 'GUI' ]
    ctxenv = ENVI.SalomeEnviron(config, ENVI.Environ(dict(os.environ)), True)
    ctxenv.silent = True
    ctxenv.set_full_environ(logger, config.APPLICATION.products.keys())

    dicdir = {}
    for p in products_list:
        prod_env = p + "_ROOT_DIR"
        val = os.getenv(prod_env)
        if os.getenv(prod_env) is None:
            if p not in config.APPLICATION.products:
                msg = _("product %s is not defined. Include it in the application or define $%s.") % \
                       (p, prod_env)
                logger.error(UTS.red(msg))
                val = ""
            val = ctxenv.environ.environ[prod_env]
        dicdir[p] = val

    # the dictionary requires all keys 
    # but the generation requires only values for KERNEL and GUI
    context = {
        "update": 1,
        "makeflags": "-j2",
        "kernel": dicdir["KERNEL"],
        "gui":    dicdir["GUI"],
        "yacs":   "",
        "med":    "",
        "mesh":   "",
        "visu":   "",
        "geom":   "",
    }
    return context

def check_module_generator(directory=None):
    """Check if module_generator is available.
    
    :param directory: (str) The directory of YACSGEN.
    :return: (str) 
      The YACSGEN path if the module_generator is available, else None
    """
    undo = False
    if directory is not None and directory not in sys.path:
        sys.path.insert(0, directory)
        undo = True
    
    res = None
    try:
        #import module_generator
        info = imp.find_module("module_generator")
        res = info[1]
    except ImportError:
        if undo:
            sys.path.remove(directory)
        res = None

    return res

def check_yacsgen(config, directory, logger):
    """Check if YACSGEN is available.
    
    :param config: (Config) The global configuration.
    :param directory: (str) The directory given by option --yacsgen
    :param logger: (Logger) The logger instance
    :return: (RCO.ReturnCode) 
      with value The path to yacsgen directory if ok
    """
    # first check for YACSGEN (command option, then product, then environment)
    yacsgen_dir = None
    yacs_src = "?"
    if directory is not None:
        yacsgen_dir = directory
        yacs_src = _("Using YACSGEN from command line")
    elif 'YACSGEN' in config.APPLICATION.products:
        yacsgen_info = PROD.get_product_config(config, 'YACSGEN')
        yacsgen_dir = yacsgen_info.install_dir
        yacs_src = _("Using YACSGEN from application")
    elif os.environ.has_key("YACSGEN_ROOT_DIR"):
        yacsgen_dir = os.getenv("YACSGEN_ROOT_DIR")
        yacs_src = _("Using YACSGEN from environment")

    if yacsgen_dir is None:
        RCO.ReturnCode("KO", _("The generate command requires YACSGEN."))
    
    logger.info("  %s in %s" % (yacs_src, yacsgen_dir))

    if not os.path.exists(yacsgen_dir):
        msg = _("YACSGEN directory not found: '%s'") % yacsgen_dir
        RCO.ReturnCode("KO", msg)
    
    # load module_generator
    c = check_module_generator(yacsgen_dir)
    if c is not None:
        return RCO.ReturnCode("OK", "check_module_generator on %s" % yacsgen_dir, c)
    
    pv = os.getenv("PYTHON_VERSION")
    if pv is None:
        python_info = PROD.get_product_config(config, "Python")
        pv = '.'.join(python_info.version.split('.')[:2])
    assert pv is not None, "$PYTHON_VERSION not defined"
    yacsgen_dir = os.path.join(yacsgen_dir, "lib", "python%s" % pv, "site-packages")
    c = check_module_generator(yacsgen_dir)
    if c is not None:
        return RCO.ReturnCode("OK", "check_module_generator on %s" % yacsgen_dir, c)

    return RCO.ReturnCode("KO", _("The python module module_generator was not found in YACSGEN"))

