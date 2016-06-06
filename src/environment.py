#!/usr/bin/env python
#-*- coding:utf-8 -*-
#  Copyright (C) 2010-2013  CEA/DEN
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
import string
import sys

import src

class Environ:
    '''Class to manage the environment context
    '''
    def __init__(self, environ=None):
        '''Initialization. If the environ argument is passed, the environment
           will be add to it, else it is the external environment.
           
        :param environ dict:  
        '''
        if environ is not None:
            self.environ = environ
        else:
            self.environ = os.environ

    def __repr__(self):
        """easy non exhaustive quick resume for debug print
        """
        res={}
        res["environ"]=self.environ
        return self.__class__.__name__ + str(res)[0:-1] + " ...etc...}"

    def _expandvars(self, value):
        '''replace some $VARIABLE into its actual value in the environment
        
        :param value str: the string to be replaced
        :return: the replaced variable
        :rtype: str
        '''
        if "$" in value:
            # The string.Template class is a string class 
            # for supporting $-substitutions
            zt = string.Template(value)
            try:
                value = zt.substitute(self.environ)
            except KeyError as exc:
                raise src.SatException(_("Missing definition "
                                         "in environment: %s") % str(exc))
        return value

    def append_value(self, key, value, sep=os.pathsep):
        '''append value to key using sep
        
        :param key str: the environment variable to append
        :param value str: the value to append to key
        :param sep str: the separator string
        '''
        # check if the key is already in the environment
        if key in self.environ:
            value_list = self.environ[key].split(sep)
            # Check if the value is already in the key value or not
            if not value in value_list:
                value_list.append(value)
            else:
                value_list.append(value_list.pop(value_list.index(value)))
            self.set(key, sep.join(value_list))
        else:
            self.set(key, value)

    def append(self, key, value, sep=os.pathsep):
        '''Same as append_value but the value argument can be a list
        
        :param key str: the environment variable to append
        :param value str or list: the value(s) to append to key
        :param sep str: the separator string
        '''
        if isinstance(value, list):
            for v in value:
                self.append_value(key, v, sep)
        else:
            self.append_value(key, value, sep)

    def prepend_value(self, key, value, sep=os.pathsep):
        '''prepend value to key using sep
        
        :param key str: the environment variable to prepend
        :param value str: the value to prepend to key
        :param sep str: the separator string
        '''
        if key in self.environ:
            value_list = self.environ[key].split(sep)
            if not value in value_list:
                value_list.insert(0, value)
            else:
                value_list.insert(0, value_list.pop(value_list.index(value)))
            self.set(key, sep.join(value_list))
        else:
            self.set(key, value)

    def prepend(self, key, value, sep=os.pathsep):
        '''Same as prepend_value but the value argument can be a list
        
        :param key str: the environment variable to prepend
        :param value str or list: the value(s) to prepend to key
        :param sep str: the separator string
        '''
        if isinstance(value, list):
            for v in value:
                self.prepend_value(key, v, sep)
        else:
            self.prepend_value(key, value, sep)

    def is_defined(self, key):
        '''Check if the key exists in the environment
        
        :param key str: the environment variable to check
        '''
        return self.environ.has_key(key)

    def set(self, key, value):
        '''Set the environment variable "key" to value "value"
        
        :param key str: the environment variable to set
        :param value str: the value
        '''
        self.environ[key] = self._expandvars(value)

    def get(self, key):
        '''Get the value of the environment variable "key"
        
        :param key str: the environment variable
        '''
        if key in self.environ:
            return self.environ[key]
        else:
            return ""

    def command_value(self, key, command):
        '''Get the value given by the system command "command" 
           and put it in the environment variable key
        
        :param key str: the environment variable
        :param command str: the command to execute
        '''
        value = subprocess.Popen(command,
                                 shell=True,
                                 stdout=subprocess.PIPE,
                                 env=self.environ).communicate()[0]
        self.environ[key] = value


class SalomeEnviron:
    """Class to manage the environment of SALOME.
    """

    def __init__(self, cfg, environ, forBuild=False):
        '''Initialization.

        :param cfg Config: the global config
        :param environ Environ: the Environ instance where 
                                to store the environment variables
        :param forBuild bool: If true, it is a launch environment, 
                              else a build one
        '''
        self.environ = environ
        self.cfg = cfg
        self.forBuild = forBuild
        self.silent = False

    def __repr__(self):
        """easy non exhaustive quick resume for debug print"""
        res={}
        res["environ"]=str(self.environ)
        res["forBuild"]=self.forBuild
        return self.__class__.__name__ + str(res)[0:-1] + " ...etc...}"

    def append(self, key, value, sep=os.pathsep):
        '''append value to key using sep
        
        :param key str: the environment variable to append
        :param value str: the value to append to key
        :param sep str: the separator string
        '''
        return self.environ.append(key, value, sep)

    def prepend(self, key, value, sep=os.pathsep):
        '''prepend value to key using sep
        
        :param key str: the environment variable to prepend
        :param value str: the value to prepend to key
        :param sep str: the separator string
        '''
        return self.environ.prepend(key, value, sep)

    def is_defined(self, key):
        '''Check if the key exists in the environment
        
        :param key str: the environment variable to check
        '''
        return self.environ.is_defined(key)

    def get(self, key):
        '''Get the value of the environment variable "key"
        
        :param key str: the environment variable
        '''
        return self.environ.get(key)

    def set(self, key, value):
        '''Set the environment variable "key" to value "value"
        
        :param key str: the environment variable to set
        :param value str: the value
        '''
        # check if value needs to be evaluated
        if value is not None and value.startswith("`") and value.endswith("`"):
            res = subprocess.Popen("echo %s" % value,
                                   shell=True,
                                   stdout=subprocess.PIPE).communicate()
            value = res[0].strip()

        return self.environ.set(key, value)

    def dump(self, out):
        """Write the environment to out
        
        :param out file: the stream where to write the environment
        """
        for k in self.environ.environ.keys():
            try:
                value = self.get(k)
            except:
                value = "?"
            out.write("%s=%s\n" % (k, value))

    def add_line(self, nb_line):
        """Add empty lines to the out stream (in case of file generation)
        
        :param nb_line int: the number of empty lines to add
        """
        if 'add_line' in dir(self.environ):
            self.environ.add_line(nb_line)

    def add_comment(self, comment):
        """Add a commentary to the out stream (in case of file generation)
        
        :param comment str: the commentary to add
        """
        if 'add_comment' in dir(self.environ):
            self.environ.add_comment(comment)

    def add_warning(self, warning):
        """Add a warning to the out stream (in case of file generation)
        
        :param warning str: the warning to add
        """
        if 'add_warning' in dir(self.environ):
            self.environ.add_warning(warning)

    def finish(self, required):
        """Add a final instruction in the out file (in case of file generation)
        
        :param required bool: Do nothing if required is False
        """
        if 'finish' in dir(self.environ):
            self.environ.add_line(1)
            self.environ.add_comment("clean all the path")
            self.environ.finish(required)

    def set_python_libdirs(self):
        """Set some generic variables for python library paths
        """
        ver = self.get('PYTHON_VERSION')
        self.set('PYTHON_LIBDIR0', os.path.join('lib',
                                                'python' + ver,
                                                'site-packages'))
        self.set('PYTHON_LIBDIR1', os.path.join('lib64',
                                                'python' + ver,
                                                'site-packages'))
          
        self.python_lib0 = self.get('PYTHON_LIBDIR0')
        self.python_lib1 = self.get('PYTHON_LIBDIR1')

    def get_names(self, lProducts):
        """Get the products name to add in SALOME_MODULES environment variable
           It is the name of the product, except in the case where the is a 
           component name. And it has to be in SALOME_MODULES variable only 
           if has_gui = "yes"
        
        :param lProducts list: List of products to potentially add
        """
        lProdHasGui = [p for p in lProducts if 'type ' in 
                    src.product.get_product_config(self.cfg, p) and 
                    src.product.get_product_config(self.cfg, p).type=='salome']
        lProdName = []
        for ProdName in lProdHasGui:
            pi = src.product.get_product_config(self.cfg, ProdName)
            if 'component_name' in pi:
                lProdName.append(pi.component_name)
            else:
                lProdName.append(ProdName)
        return lProdName

    def set_application_env(self, logger):
        """Sets the environment defined in the APPLICATION file.
        
        :param logger Logger: The logger instance to display messages
        """
        
        # Set the variables defined in the "environ" section
        if 'environ' in self.cfg.APPLICATION:
            self.add_comment("APPLICATION environment")
            for p in self.cfg.APPLICATION.environ:
                self.set(p, self.cfg.APPLICATION.environ[p])
            self.add_line(1)

        # If there is an "environ_script" section, load the scripts
        if 'environ_script' in self.cfg.APPLICATION:
            for pscript in self.cfg.APPLICATION.environ_script:
                self.add_comment("script %s" % pscript)
                sname = pscript.replace(" ", "_")
                self.run_env_script("APPLICATION_%s" % sname,
                                self.cfg.APPLICATION.environ_script[pscript],
                                logger)
                self.add_line(1)
        
        # If there is profile (SALOME), then define additional variables
        if 'profile' in self.cfg.APPLICATION:
            profile_product = self.cfg.APPLICATION.profile.product
            product_info_profile = src.product.get_product_config(self.cfg,
                                                            profile_product)
            profile_share_salome = os.path.join(product_info_profile.install_dir,
                                                "share",
                                                "salome" )
            self.set( "SUITRoot", profile_share_salome )
            self.set( "SalomeAppConfig",
                      os.path.join(profile_share_salome,
                                   "resources",
                                   profile_product.lower() ) )
        
        # The list of products to launch
        lProductsName = self.get_names(self.cfg.APPLICATION.products.keys())
        
        self.set( "SALOME_MODULES",    ','.join(lProductsName))

    def set_salome_minimal_product_env(self, product_info, logger):
        """Sets the minimal environment for a SALOME product.
           xxx_ROOT_DIR and xxx_SRC_DIR
        
        :param product_info Config: The product description
        :param logger Logger: The logger instance to display messages        
        """
        # set root dir
        root_dir = product_info.name + "_ROOT_DIR"
        if not self.is_defined(root_dir):
            if 'install_dir' in product_info and product_info.install_dir:
                self.set(root_dir, product_info.install_dir)
            elif not self.silent:
                logger.write("  " + _("No install_dir for product %s\n") %
                              product_info.name, 5)

        # set source dir, unless no source dir
        if not src.product.product_is_fixed(product_info):
            src_dir = product_info.name + "_SRC_DIR"
            if not self.is_defined(src_dir):
                self.set(src_dir, product_info.source_dir)

    def set_salome_generic_product_env(self, product):
        """Sets the generic environment for a SALOME product.
        
        :param product str: The product name    
        """
        # get the product descritption
        pi = src.product.get_product_config(self.cfg, product)
        # Construct XXX_ROOT_DIR
        env_root_dir = self.get(pi.name + "_ROOT_DIR")
        l_binpath_libpath = []

        # create additional ROOT_DIR for CPP components
        if 'component_name' in pi:
            compo_name = pi.component_name
            if compo_name + "CPP" == product:
                compo_root_dir = compo_name + "_ROOT_DIR"
                envcompo_root_dir = os.path.join(
                            self.cfg.TOOLS.common.install_root, compo_name )
                self.set(compo_root_dir ,  envcompo_root_dir)
                bin_path = os.path.join(envcompo_root_dir, 'bin', 'salome')
                lib_path = os.path.join(envcompo_root_dir, 'lib', 'salome')
                l_binpath_libpath.append( (bin_path, lib_path) )

        appliname = 'salome'
        if (src.get_cfg_param(pi, 'product_type', 'SALOME').upper() 
                            not in [ "SALOME", "SMESH_PLUGIN", "SAMPLE" ]):
            appliname = ''

        # Construct the paths to prepend to PATH and LD_LIBRARY_PATH and 
        # PYTHONPATH
        bin_path = os.path.join(env_root_dir, 'bin', appliname)
        lib_path = os.path.join(env_root_dir, 'lib', appliname)
        l_binpath_libpath.append( (bin_path, lib_path) )

        for bin_path, lib_path in l_binpath_libpath:
            if not self.forBuild:
                self.prepend('PATH', bin_path)
                if src.architecture.is_windows():
                    self.prepend('PATH', lib_path)
                else :
                    self.prepend('LD_LIBRARY_PATH', lib_path)

            l = [ bin_path, lib_path,
                  os.path.join(env_root_dir, self.python_lib0, appliname),
                  os.path.join(env_root_dir, self.python_lib1, appliname)
                ]
            self.prepend('PYTHONPATH', l)

    def load_cfg_environment(self, cfg_env):
        """Loads environment defined in cfg_env 
        
        :param cfg_env Config: A config containing an environment    
        """
        # Loop on cfg_env values
        for env_def in cfg_env:
            val = cfg_env[env_def]
            
            # if it is env_script, do not do anything (reserved keyword)
            if env_def == "env_script":
                continue
            
            # if it is a dict, do not do anything
            if isinstance(val, src.pyconf.Mapping):
                continue

            # if it is a list, loop on its values
            if isinstance(val, src.pyconf.Sequence):
                # transform into list of strings
                l_val = []
                for item in val:
                    l_val.append(item)
                val = l_val

            # "_" means that the value must be prepended
            if env_def.startswith("_"):
                # separator exception for PV_PLUGIN_PATH
                if env_def[1:] == 'PV_PLUGIN_PATH':
                    self.prepend(env_def[1:], val, ';')
                else:
                    self.prepend(env_def[1:], val)
            elif env_def.endswith("_"):
                # separator exception for PV_PLUGIN_PATH
                if env_def[:-1] == 'PV_PLUGIN_PATH':
                    self.append(env_def[:-1], val, ';')
                else:
                    self.append(env_def[:-1], val)
            else:
                self.set(env_def, val)

    def set_a_product(self, product, logger):
        """Sets the environment of a product. 
        
        :param product str: The product name
        :param logger Logger: The logger instance to display messages
        """
        
        # Get the informations corresponding to the product
        pi = src.product.get_product_config(self.cfg, product)
        
        # Do not define environment if the product is native
        if src.product.product_is_native(pi):
            return
        
        if not self.silent:
            logger.write(_("Setting environment for %s\n") % product, 4)

        self.add_line(1)
        self.add_comment('setting environ for ' + product)

        # Put the environment define in the configuration of the product
        if "environ" in pi:
            self.load_cfg_environment(pi.environ)
            if self.forBuild and "build" in pi.environ:
                self.load_cfg_environment(pi.environ.build)
            if not self.forBuild and "launch" in pi.environ:
                self.load_cfg_environment(pi.environ.launch)
            # if product_info defines a env_scripts, load it
            if 'env_script' in pi.environ:
                self.run_env_script(pi, logger)

        # Set an additional environment for SALOME products
        if src.product.product_is_salome(pi):
            # set environment using definition of the product
            self.set_salome_minimal_product_env(pi, logger)
            self.set_salome_generic_product_env(product)
            

    def run_env_script(self, product_info, logger=None):
        """Runs an environment script. 
        
        :param product_info Config: The product description
        :param logger Logger: The logger instance to display messages
        """
        env_script = product_info.environ.env_script
        # Check that the script exists
        if not os.path.exists(env_script):
            raise src.SatException(_("Environment script not found: %s") % 
                                   env_script)

        if not self.silent and logger is not None:
            logger.write("  ** load %s\n" % env_script, 4)

        # import the script and run the set_env function
        try:
            import imp
            pyproduct = imp.load_source(product_info.name + "_env_script",
                                        env_script)
            pyproduct.set_env(self, product_info.install_dir,
                              product_info.version)
        except:
            __, exceptionValue, exceptionTraceback = sys.exc_info()
            print(exceptionValue)
            import traceback
            traceback.print_tb(exceptionTraceback)
            traceback.print_exc()

    def run_simple_env_script(self, script_path, logger=None):
        """Runs an environment script. Same as run_env_script, but with a 
           script path as parameter.
        
        :param script_path str: a path to an environment script
        :param logger Logger: The logger instance to display messages
        """
        # Check that the script exists
        if not os.path.exists(script_path):
            raise src.SatException(_("Environment script not found: %s") % 
                                   script_path)

        if not self.silent and logger is not None:
            logger.write("  ** load %s\n" % script_path, 4)

        script_basename = os.path.basename(script_path)
        if script_basename.endswith(".py"):
            script_basename = script_basename[:-len(".py")]

        # import the script and run the set_env function
        try:
            import imp
            pyproduct = imp.load_source(script_basename + "_env_script",
                                        script_path)
            pyproduct.load_env(self)
        except:
            __, exceptionValue, exceptionTraceback = sys.exc_info()
            print(exceptionValue)
            import traceback
            traceback.print_tb(exceptionTraceback)
            traceback.print_exc()

    def set_products(self, logger, src_root=None):
        """Sets the environment for all the products. 
        
        :param logger Logger: The logger instance to display messages
        :param src_root src: the application working directory
        """
        self.add_line(1)
        self.add_comment('setting environ for all products')

        self.set_python_libdirs()

        # Set the application working directory
        if src_root is None:
            src_root = self.cfg.APPLICATION.workdir
        self.set('SRC_ROOT', src_root)

        # SALOME variables
        appli_name = "APPLI"
        if "APPLI" in self.cfg and "application_name" in self.cfg.APPLI:
            appli_name = self.cfg.APPLI.application_name
        self.set("SALOME_APPLI_ROOT",
                 os.path.join(self.cfg.APPLICATION.workdir, appli_name))

        # The loop on the products
        for product in self.cfg.APPLICATION.products.keys():
            self.set_a_product(product, logger)
            self.finish(False)
 
    def set_full_environ(self, logger, env_info):
        """Sets the full environment for products 
           specified in env_info dictionary. 
        
        :param logger Logger: The logger instance to display messages
        :param env_info list: the list of products
        """
        # set product environ
        self.set_application_env(logger)

        self.set_python_libdirs()

        # set products        
        for product in env_info:
            self.set_a_product(product, logger)

class FileEnvWriter:
    """Class to dump the environment to a file.
    """
    def __init__(self, config, logger, out_dir, src_root, env_info=None):
        '''Initialization.

        :param cfg Config: the global config
        :param logger Logger: The logger instance to display messages
        :param out_dir str: The directory path where t put the output files
        :param src_root str: The application working directory
        :param env_info str: The list of products to add in the files.
        '''
        self.config = config
        self.logger = logger
        self.out_dir = out_dir
        self.src_root= src_root
        self.silent = True
        self.env_info = env_info

    def write_env_file(self, filename, forBuild, shell):
        """Create an environment file.
        
        :param filename str: the file path
        :param forBuild bool: if true, the build environment
        :param shell str: the type of file wanted (.sh, .bat)
        :return: The path to the generated file
        :rtype: str
        """
        if not self.silent:
            self.logger.write(_("Create environment file %s\n") % 
                              src.printcolors.printcLabel(filename), 3)

        # create then env object
        env_file = open(os.path.join(self.out_dir, filename), "w")
        tmp = src.fileEnviron.get_file_environ(env_file,
                                               shell,
                                               {})
        env = SalomeEnviron(self.config, tmp, forBuild)
        env.silent = self.silent

        # Set the environment
        if self.env_info is not None:
            env.set_full_environ(self.logger, self.env_info)
        else:
            # set env from the APPLICATION
            env.set_application_env(self.logger)
            # set the products
            env.set_products(self.logger,
                            src_root=self.src_root)

        # add cleanup and close
        env.finish(True)
        env_file.close()

        return env_file.name
   
    def write_cfgForPy_file(self, filename, additional_env = {}):
        """Append to current opened aFile a cfgForPy 
           environment (SALOME python launcher).
           
        :param filename str: the file path
        :param additional_env dict: a dictionary of additional variables 
                                    to add to the environment
        """
        if not self.silent:
            self.logger.write(_("Create configuration file %s\n") % 
                              src.printcolors.printcLabel(aFile.name), 3)

        # create then env object
        tmp = src.fileEnviron.get_file_environ(filename, 
                                               "cfgForPy", 
                                               {})
        # environment for launch
        env = SalomeEnviron(self.config, tmp, forBuild=False)
        env.silent = self.silent

        if self.env_info is not None:
            env.set_full_environ(self.logger, self.env_info)
        else:
            # set env from PRODUCT
            env.set_application_env(self.logger)

            # set the products
            env.set_products(self.logger,
                            src_root=self.src_root)

        # Add the additional environment if it is not empty
        if len(additional_env) != 0:
            for variable in additional_env:
                env.set(variable, additional_env[variable])

        # add cleanup and close
        env.finish(True)

class Shell:
    """Definition of a Shell.
    """
    def __init__(self, name, extension):
        '''Initialization.

        :param name str: the shell name
        :param extension str: the shell extension
        '''
        self.name = name
        self.extension = extension

def load_environment(config, build, logger):
    """Loads the environment (used to run the tests, for example).
    
    :param config Config: the global config
    :param build bool: build environement if True
    :param logger Logger: The logger instance to display messages
    """
    environ = SalomeEnviron(config, Environ(os.environ), build)
    environ.set_application_env(logger)
    environ.set_products(logger)
    environ.finish(True)