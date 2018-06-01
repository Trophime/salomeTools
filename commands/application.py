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

"""
Is a salomeTools command module
see Command class docstring, also used for help
"""

import os
import getpass
import subprocess as SP

import src.ElementTree as ETREE
import src.debug as DBG
import src.returnCode as RCO
import src.utilsSat as UTS
import src.product as PROD
from src.salomeTools import _BaseCommand
import src.environment as ENVI

########################################################################
# Command class
########################################################################
class Command(_BaseCommand):
  """
  The application command creates a SALOME application. 

  | Warning:
  |   It works only for SALOME 6.
  |   Use the 'launcher' command for newer versions of SALOME
  | 
  | Examples:
  | >> sat application SALOME-6.6.0
  """
  
  name = "application"
  
  def getParser(self):
    """Define all options for command 'sat application <options>'"""
    parser = self.getParserWithHelp()
    parser.add_option(
        'n', 'name', 'string', 'name',
        _("""\
Optional: The name of the application 
          (default is APPLICATION.virtual_app.name or runAppli)""") )
    parser.add_option(
        'c', 'catalog', 'string', 'catalog',
        _('Optional: The resources catalog to use') )
    parser.add_option(
        't', 'target', 'string', 'target',
        _("""\
Optional: The directory where to create the application
          (default is APPLICATION.workdir)""") )
    parser.add_option(
        '', 'gencat', 'string', 'gencat',
        _("""\
Optional: Create a resources catalog for the specified machines (separated with ',')
Note:     this command will ssh to retrieve information to each machine in the list""") )
    parser.add_option(
        'm', 'module', 'list2', 'modules',
        _("Optional: the restricted list of module(s) to include in the application") )
    return parser

  def run(self, cmd_arguments):
    """method called for command 'sat application <options>'"""
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
    
    # check for APPLICATION
    returnCode = UTS.check_config_has_application(config)
    if not returnCode.isOk(): return returnCode

    application = config.VARS.application
    logger.info(_("Building application for <header>%s<reset>\n") % application)

    # if section APPLICATION.virtual_app does not exists create one
    if "virtual_app" not in config.APPLICATION:
        msg = _("The section APPLICATION.virtual_app is not defined in the product.")
        logger.error(UTS.red(msg))
        return RCO.ReturnCode("KO", msg)
    virtual_app = config.APPLICATION.virtual_app
    
    # get application dir
    target_dir = config.APPLICATION.workdir
    if options.target:
        target_dir = options.target

    # set list of modules
    if options.modules:
        virtual_app['modules'] = options.modules

    # set name and application_name
    if options.name:
        virtual_app['name'] = options.name
        virtual_app['application_name'] = options.name + "_appdir"
    
    default = config.APPLICATION.virtual_app.name + "_appdir"
    application_name = UTS.get_config_key(virtual_app, "application_name", default)
    appli_dir = os.path.join(target_dir, application_name)

    fmt = "  %s = %s\n" # as "  label = value\n"
    logger.info(fmt % (_("Application directory"), appli_dir))
    
    # get catalog
    catalog = ""
    catalog_src = ""
    if options.catalog:
        # use catalog specified in the command line
        catalog = options.catalog
    elif options.gencat:
        # generate catalog for given list of computers
        catalog_src = options.gencat
        catalog = UTS.generate_catalog(options.gencat.split(","), config,logger)
    elif 'catalog' in virtual_app:
        # use catalog specified in the product
        if virtual_app.catalog.endswith(".xml"):
            # catalog as a file
            catalog = virtual_app.catalog
        else:
            # catalog as a list of computers
            catalog_src = virtual_app.catalog
            mlist = filter(lambda l: len(l.strip()) > 0, virtual_app.catalog.split(","))
            if len(mlist) > 0:
                catalog = UTS.generate_catalog(virtual_app.catalog.split(","), config, logger)

    # display which catalog is used
    if len(catalog) > 0:
        catalog = os.path.realpath(catalog)
        if len(catalog_src) > 0:
            logger.info(fmt % (_("Resources Catalog"), catalog_src))
        else:
            logger.info(fmt % (_("Resources Catalog"), catalog))

    # remove previous application
    if os.path.exists(appli_dir):
        logger.info(get_step(_("Removing previous application directory")))
        shutil.rmtree(appli_dir)

    # generate the application
    retcode = create_application(config, appli_dir, catalog, logger)
    
    return retcode


def make_alias(appli_path, alias_path, force=False):
    """Creates an alias for runAppli"""
    assert len(alias_path) > 0, "Bad name for alias"
    if os.path.exists(alias_path) and not force:
        raise Exception(_("Cannot create the alias '%s'\n") % alias_path)
    else: # find relative path
        os.symlink(appli_path, alias_path)

def add_module_to_appli(out, module, has_gui, module_path, logger, flagline):
    """add the definition of a module to out stream."""
    if not os.path.exists(module_path):
        if not flagline:
            logger.info("\n")
            flagline = True
        logger.warning("  %s\n" + _("module %s not installed") % module)

    out.write('   <module name="%s" gui="%s" path="%s"/>\n' % \
              (module, has_gui, module_path))
    return flagline

def create_config_file(config, modules, env_file, logger):
    """Creates the config file to create an application with the list of modules."""
    samples = ""
    if 'SAMPLES' in config.APPLICATION.products:
        samples = PROD.get_product_config(config, 'SAMPLES').source_dir

    config_file = UTS.get_tmp_filename(config, "appli_config.xml")
    f = open(config_file, "w")

    f.write('<application>\n')
    if env_file.endswith("cfg"):
        f.write('<context path="%s"/>\n' % env_file)
    else:   
        f.write('<prerequisites path="%s"/>\n' % env_file)
    f.write('<resources path="CatalogResources.xml"/>\n')
    f.write('<modules>\n')

    flagline = False
    for m in modules:
        mm = PROD.get_product_config(config, m)
        if PROD.product_is_smesh_plugin(mm):
            continue

        if 'install_dir' in mm and bool(mm.install_dir):
            if PROD.product_is_cpp(mm):
                # cpp module
                for aa in PROD.get_product_components(mm):
                    install_dir = os.path.join(config.APPLICATION.workdir,
                                               "INSTALL")
                    mp = os.path.join(install_dir, aa)
                    flagline = add_module_to_appli(f,
                                                   aa,
                                                   "yes",
                                                   mp,
                                                   logger,
                                                   flagline)
            else:
                # regular module
                mp = mm.install_dir
                gui = UTS.get_config_key(mm, "has_gui", "yes")
                flagline = add_module_to_appli(f, m, gui, mp, logger, flagline)

    f.write('</modules>\n')
    f.write('<samples path="%s"/>\n' % samples)
    f.write('</application>\n')
    f.close()

    return config_file


def customize_app(config, appli_dir, logger):
    """Customizes the application by editing SalomeApp.xml."""
    if 'configure' not in config.APPLICATION.virtual_app \
        or len(config.APPLICATION.virtual_app.configure) == 0:
        return RCO.ReturnCode("OK", "Nothing in configure")

    def get_element(parent, name, strtype):
        """shortcut to get an element (section or parameter) from parent."""
        for c in parent.getchildren():
            if c.attrib['name'] == name:
                return c

        # element not found create it
        elt = add_simple_node(parent, strtype)
        elt.attrib['name'] = name
        return elt

    def add_simple_node(parent, node_name, text=None):
        """shortcut method to create a node"""
        n = ETREE.Element(node_name)
        if text is not None:
            try:
                n.text = text.strip("\n\t").decode("UTF-8")
            except:
                logger.error("problem decode UTF8 %s:\n%s\n" % \
                   (node_name, UTS.toHex(text)))
                n.text = "?"
        parent.append(n)
        return n

    # read the app file
    app_file = os.path.join(appli_dir, "SalomeApp.xml")
    tree = ETREE.parse(app_file)
    document = tree.getroot()
    assert document is not None, "document tag not found"

    for section_name in config.APPLICATION.virtual_app.configure:
        for parameter_name in config.APPLICATION.virtual_app.configure[section_name]:
            parameter_value = config.APPLICATION.virtual_app.configure[section_name][parameter_name]
            logger.info("  configure: %s/%s = %s\n" % (section_name,
                                                        parameter_name,
                                                        parameter_value))
            section = get_element(document, section_name, "section")
            parameter = get_element(section, parameter_name, "parameter")
            parameter.attrib['value'] = parameter_value

    # write the file
    with open(app_file, "w") as f:
      f.write("<?xml version='1.0' encoding='utf-8'?>\n")
      f.write(ETREE.tostring(document, encoding='utf-8'))
    return RCO.ReturnCode("OK", "customize %s done" % app_file)

def generate_application(config, appli_dir, config_file, logger):
    """Generates the application with the config_file."""
    target_dir = os.path.dirname(appli_dir)

    install_KERNEL_dir = PROD.get_product_config(config, 'KERNEL').install_dir
    script = os.path.join(install_KERNEL_dir, "bin", "salome", "appli_gen.py")
    if not os.path.exists(script):
        raise Exception(_("KERNEL is not installed"))
    
    # Add SALOME python in the environment in order to avoid python version 
    # problems at appli_gen.py call
    if 'Python' in config.APPLICATION.products:
        envi = ENVI.SalomeEnviron(config, ENVI.Environ(dict(os.environ)), True)
        envi.set_a_product('Python', logger)
    
    command = """
set -x
which python
python %s --prefix=%s --config=%s
""" % (script, appli_dir, config_file)
    res = UTS.Popen(command, shell=True, cwd=target_dir, env=envi.environ.environ, logger=logger)  
    res.raiseIfKo()
    return res

def get_step(logger, message, pad=50):
    """
    returns 'message ........ ' with pad 50 by default
    avoid colors '<color>' for now in message
    """
    return "%s %s " % (message, '.'*(pad - len(message.decode("UTF-8"))))

def create_application(config, appli_dir, catalog, logger, display=True):
    """Creates a SALOME application."""  
    SALOME_modules = get_SALOME_modules(config)
    
    warn = ['KERNEL', 'GUI']
    if display:
        for w in warn:
            if w not in SALOME_modules:
                msg = _("module %s is required to create application") % w
                logger.warning(msg)

    # generate the launch file
    retcode = generate_launch_file(config, appli_dir, catalog, logger, SALOME_modules)
    cmd = UTS.label(os.path.join(appli_dir, "salome"))
    
    if not retcode.isOk():
        logger.error("Problem generating %s" % cmd)
        return retcode

    if display:
        msg = _("To launch the application, type:")
        logger.info("\n%s\n  %s" % (msg, cmd))
    return retcode

def get_SALOME_modules(config):
    l_modules = []
    for product in config.APPLICATION.products:
        product_info = PROD.get_product_config(config, product)
        if (PROD.product_is_SALOME(product_info) or 
               PROD.product_is_generated(product_info)):
            l_modules.append(product)
    return l_modules

def generate_launch_file(config, appli_dir, catalog, logger, l_SALOME_modules):
    """
    Obsolescent way of creating the application.
    This method will use appli_gen to create the application directory.
    """
    if len(catalog) > 0 and not os.path.exists(catalog):
        raise IOError(_("Catalog not found: %s") % catalog)
    
    logger.info(get_step(_("Creating environment files")))

    VersionSalome = UTS.get_salome_version(config)
    if VersionSalome >= 820:
        # for salome 8+ we use a salome context file for the virtual app
        app_shell="cfg"
        env_ext="cfg"
    else:
        app_shell="bash"
        env_ext="sh"

    import environ
    # generate only shells the user wants (by default bash, csh, batch)
    # the environ command will only generate file compatible 
    # with the current system.
    environ.write_all_source_files(config, logger, shells=[app_shell], silent=True)

    # build the application (the name depends upon salome version
    env_file = os.path.join(config.APPLICATION.workdir, "env_launch." + env_ext)

    logger.info(get_step(_("Building application")))
    cf = create_config_file(config, l_SALOME_modules, env_file, logger)

    # create the application directory
    os.makedirs(appli_dir)

    # generate the application
    retcode = generate_application(config, appli_dir, cf, logger) 
    if not retcode.isOk(): 
      return retcode
    retcode = customize_app(config, appli_dir, logger)
    if not retcode.isOk(): 
      return retcode
    
    # copy the catalog if one
    if len(catalog) > 0:
        shutil.copy(catalog, os.path.join(appli_dir, "CatalogResources.xml"))

    return RCO.ReturnCode("OK", "generate_launch_file done")



