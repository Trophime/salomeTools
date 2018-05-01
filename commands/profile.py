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

import shutil
import subprocess

import src.debug as DBG
import src.returnCode as RCO
import src.pyconf as PYCONF
from src.salomeTools import _BaseCommand

########################################################################
# Command class
########################################################################
class Command(_BaseCommand):
  """\
  The profile command creates default profile.
  
  | examples: 
  | >> sat profile [PRODUCT] 
  | >> sat profile --prefix (string)
  | >> sat profile --name (string)
  | >> sat profile --force
  | >> sat profile --version (string) 
  | >> sat profile --slogan (string) 
  """
  
  name = "profile"
  
  def getParser(self):
    """Define all options for command 'sat profile <options>'"""
    parser = self.getParserWithHelp()
    parser.add_option(
        'p', 'prefix', 'string', 'prefix', 
        _("Where the profile's sources will be generated.") )
    parser.add_option(
        'n', 'name', 'string', 'name', 
        _("Name of the profile's sources. [Default: '${config.PRODUCT.name}_PROFILE]") )
    parser.add_option(
        'f', 'force', 'boolean', 'force',
        _("Overwrites existing sources.") )
    parser.add_option(
        'u', 'no_update', 'boolean', 'no_update', 
        _("Does not update pyconf file.") )
    parser.add_option(
        'v', 'version', 'string', 'version', 
        _("Version of the application. [Default: 1.0]"), '1.0' )
    parser.add_option(
        's', 'slogan', 'string', 'slogan', 
        _("Slogan of the application.") )
    return parser

  def run(self, cmd_arguments):
    """method called for command 'sat profile <options>'""" 
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
  
    src.check_config_has_application(config)

    if options.prefix is None:
        msg = _("The --%s argument is required\n") % "prefix"
        logger.error(msg)
        return RCO.ReturnCode("KO", msg)
    
    retcode = generate_profile_sources(config, options, logger)

    if not options.no_update :
        update_pyconf(config, options)

    return retcode


# Class that overrides common.Reference
# in order to manipulate fields starting with '@'
class profileReference( PYCONF.Reference ):
    def __str__(self):
        s = self.elements[0]
        for tt, tv in self.elements[1:]:
            if tt == PYCONF.DOT:
                s += '.%s' % tv
            else:
                s += '[%r]' % tv
        if self.type == PYCONF.BACKTICK:
            return PYCONF.BACKTICK + s + PYCONF.BACKTICK
        elif self.type == PYCONF.AT:
            return PYCONF.AT + s
        else:
            return PYCONF.DOLLAR + s

##
# Class that overrides how fields starting with '@' are read.
class profileConfigReader( PYCONF.ConfigReader ) :
    def parseMapping(self, parent, suffix):
        if self.token[0] == PYCONF.LCURLY:
            self.match(PYCONF.LCURLY)
            rv = PYCONF.Mapping(parent)
            rv.setPath(
               PYCONF.makePath(object.__getattribute__(parent, 'path'),
                                   suffix))
            self.parseMappingBody(rv)
            self.match(PYCONF.RCURLY)
        else:
            self.match(PYCONF.AT)
            __, fn = self.match('"')
            rv = profileReference(self, PYCONF.AT, fn)
        return rv



##
# Gets the profile name
def get_profile_name ( options, config ):
    if options.name :
        res = options.name
    else :
        res = config.APPLICATION.name + "_PROFILE"
    return res

def generate_profile_sources( config, options, logger ):
    """
    Generates the sources of the profile
    """
    #Check script app-quickstart.py exists
    kernel_cfg = src.product.get_product_config(config, "KERNEL")
    kernel_root_dir = kernel_cfg.install_dir
    if not src.product.check_installation(kernel_cfg):
        raise Exception(_("KERNEL is not installed"))
    script = os.path.join(kernel_root_dir,"bin","salome","app-quickstart.py")
    if not os.path.exists( script ):
        raise Exception( _("KERNEL's install has not the script app-quickstart.py") )

    # Check that GUI is installed
    gui_cfg = src.product.get_product_config(config, "GUI")
    gui_root_dir = gui_cfg.install_dir
    if not src.product.check_installation(gui_cfg):
        raise Exception(_("GUI is not installed"))

    #Set prefix option passed to app-quickstart.py
    name = get_profile_name ( options, config )
    prefix = os.path.join( options.prefix, name )
    if os.path.exists( prefix ) :
        if not options.force :
            raise Exception( 
              _("The path %s already exists, use option --force to remove it.") % prefix )
        else :
            shutil.rmtree( prefix )

    #Set name option passed to app-quickstart.py
    if name.upper().endswith("_PROFILE"):
        name = name[:-8]

    #Write command line that calls app-quickstart.py
    command = "python %s --prefix=%s --name=%s --modules=_NO_ --version=%s" % \
              ( script, prefix, name, options.version )
    if options.force :
        command += " --force"
    if options.slogan :
        command += " --slogan=%s" % options.slogan
    logger.debug("\n>" + command + "\n")

    #Run command
    os.environ["KERNEL_ROOT_DIR"] = kernel_root_dir
    os.environ["GUI_ROOT_DIR"] = gui_root_dir
    res = subprocess.call(command,
                    shell=True,
                    env=os.environ,
                    stdout=logger.logTxtFile,
                    stderr=subprocess.STDOUT)
    #Check result of command
    if res != 0:
        raise Exception(_("Cannot create application, code = %d\n") % res)
    else:
        logger.info( _("Profile sources were generated in directory %s.\n" % prefix) )
    return res


def update_pyconf( config, options, logger ):
    """
    Updates the pyconf
    """
    #Save previous version
    pyconf = config.VARS.product + '.pyconf'
    pyconfBackup = config.VARS.product + '-backup.pyconf'
    logger.info( _("Updating %s (previous version saved as %s." ) % (pyconf, pyconfBackup))
    path = config.getPath( pyconf )
    shutil.copyfile( os.path.join( path, pyconf ),
                     os.path.join( path, pyconfBackup ) )

    #Load config
    cfg = PYCONF.Config( )
    object.__setattr__( cfg, 'reader', profileConfigReader( cfg ) )
    cfg.load( PYCONF.defaultStreamOpener( os.path.join( path, pyconf ) ) )

    #Check if profile is in APPLICATION.products
    profile = get_profile_name ( options, config )
    if not profile in cfg.APPLICATION.products:
        cfg.APPLICATION.products.append( profile, None )

    #Check if profile is in APPLICATION
    if not 'profile' in cfg.APPLICATION:
        cfg.APPLICATION.addMapping( 'profile', PYCONF.Mapping(), None )
        cfg.APPLICATION.profile.addMapping( 'module', profile, None )
        cfg.APPLICATION.profile.addMapping( 'launcher_name',
                                            config.VARS.product.lower(), None )

    #Check if profile info is in PRODUCTS
    if not 'PRODUCTS' in cfg:
        cfg.addMapping( 'PRODUCTS', PYCONF.Mapping(), None )
        
    if not profile in cfg.PRODUCTS:
        cfg.PRODUCTS.addMapping( profile, PYCONF.Mapping(), None )
        cfg.PRODUCTS[profile].addMapping( 'default', PYCONF.Mapping(),
                                          None )
        prf = cfg.TOOLS.common.module_info[profile].default
        prf.addMapping( 'name', profile, None )
        prf.addMapping( 'get_source', 'archive', None )
        prf.addMapping( 'build_source', 'cmake', None )
        prf.addMapping( 'archive_info', PYCONF.Mapping(), None )
        prf.archive_info.addMapping( 
            'name', os.path.join(os.path.abspath(options.prefix), profile), None )
        tmp = "APPLICATION.workdir + $VARS.sep + 'SOURCES' + $VARS.sep + $name"
        prf.addMapping( 'source_dir', 
                        PYCONF.Reference(cfg, PYCONF.DOLLAR, tmp ),
                        None )
        tmp = "APPLICATION.workdir + $VARS.sep + 'BUILD' + $VARS.sep + $name"
        prf.addMapping( 'build_dir', 
                         PYCONF.Reference(cfg, PYCONF.DOLLAR, tmp ),
                         None )
        prf.addMapping( 'depend', PYCONF.Sequence(), None )
        prf.depend.append( 'KERNEL', None )
        prf.depend.append( 'GUI', None )
        prf.depend.append( 'Python', None )
        prf.depend.append( 'Sphinx', None )
        prf.depend.append( 'qt', None )
        prf.addMapping( 'opt_depend', PYCONF.Sequence(), None )

    #Save config
    f = file( os.path.join( path, pyconf ) , 'w')
    cfg.__save__(f)
