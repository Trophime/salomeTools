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

"""
Utilities to build and compile 

| Usage:
| >> import src.compilation as COMP
"""

import os
import sys
import shutil

from src.options import OptResult
import returnCode as RCO
import src.utilsSat as UTS
import src.product as PROD
import src.environment as ENVI
import src.architecture as ARCH


C_COMPILE_ENV_LIST = "CC CXX F77 CFLAGS CXXFLAGS LIBS LDFLAGS".split()

class Builder:
    """
    Class to handle all construction steps, like cmake, configure, make, ...
    """
    def __init__(self,
                 config,
                 logger,
                 product_info,
                 options = OptResult(),
                 check_src=True):
        self.config = config
        self.logger = logger
        self.options = options
        self.product_info = product_info
        self.build_dir = UTS.Path(self.product_info.build_dir)
        self.source_dir = UTS.Path(self.product_info.source_dir)
        self.install_dir = UTS.Path(self.product_info.install_dir)
        self.header = ""
        self.debug_mode = False
        if "debug" in self.product_info and self.product_info.debug == "yes":
            self.debug_mode = True

    def prepare(self):
        """
        Prepares the environment.
        Build two environment: one for building and one for testing (launch).
        """
        # shortcuts
        logger = self.logger
        config = self.config
        
        if not self.build_dir.exists():
            # create build dir
            self.build_dir.make()

        msg = """
build_dir   = %s
install_dir = %s
""" % (str(self.build_dir), str(self.install_dir))      
        logger.trace(msg)

        # add products in depend and opt_depend list recursively
        environ_info = PROD.get_product_dependencies(config, self.product_info)
        #environ_info.append(self.product_info.name)

        # create build environment
        self.build_environ = ENVI.SalomeEnviron(config, ENVI.Environ(dict(os.environ)), True)
        self.build_environ.silent = UTS.isSilent(config.USER.output_verbose_level)
        self.build_environ.set_full_environ(logger, environ_info)
        
        # create runtime environment
        self.launch_environ = ENVI.SalomeEnviron(config, ENVI.Environ(dict(os.environ)), False)
        self.launch_environ.silent = True # no need to show here
        self.launch_environ.set_full_environ(logger, environ_info)

        msg = "build environment:\n"
        for ee in C_COMPILE_ENV_LIST:
          vv = self.build_environ.get(ee)
          if len(vv) > 0:
            msg += "  %s = %s\n" % (ee, vv)
                          
        logger.trace(msg)
        return RCO.ReturnCode("OK", "prepare done")

    def cmake(self, options=""):
        """Runs cmake with the given options."""
        cmake_option = options
        # cmake_option +=' -DCMAKE_VERBOSE_MAKEFILE=ON -DSALOME_CMAKE_DEBUG=ON'
        if 'cmake_options' in self.product_info:
            cmake_option += " %s " % " ".join(self.product_info.cmake_options.split())

        # add debug option
        if self.debug_mode:
            cmake_option += " -DCMAKE_BUILD_TYPE=Debug"
        else :
            cmake_option += " -DCMAKE_BUILD_TYPE=Release"
        
        # In case CMAKE_GENERATOR is defined in environment, 
        # use it in spite of automatically detect it
        if 'cmake_genepreparerator' in self.config.APPLICATION:
            cmake_option += " -DCMAKE_GENERATOR=%s" % \
                            self.config.APPLICATION.cmake_generator
        
        cmd = """
# CMAKE
set -x
cmake %s -DCMAKE_INSTALL_PREFIX=%s %s
""" % (cmake_option, self.install_dir, self.source_dir)

        """
        for key in sorted(self.build_environ.environ.environ.keys()):
          print key, "  ", self.build_environ.environ.environ[key]
        """
        env = self.build_environ.environ.environ
        res = UTS.Popen(cmd, cwd=str(self.build_dir),env=env)
        return res


    def build_configure(self, options=""):
        """Runs build_configure with the given options."""
        if 'buildconfigure_options' in self.product_info:
            options += " %s " % self.product_info.buildconfigure_options

        bconf = os.path.join(self.source_dir, "build_configure")
        cmd = """
set -x
%s %s
""" % (bconf, options)

        env = self.build_environ.environ.environ
        res = UTS.Popen(cmd, cwd=str(self.build_dir), env=env)
        return res


    def configure(self, options=""):
        """Runs configure with the given options."""
        if 'configure_options' in self.product_info:
            options += " %s " % self.product_info.configure_options

        conf = os.path.join(self.source_dir, "configure")
        cmd = """
set -x
%s --prefix=%s %s
""" % (conf, self.install_dir, options)

        env = self.build_environ.environ.environ
        res = UTS.Popen(cmd, cwd=str(self.build_dir), env=env)
        return res

    def hack_libtool(self):
        libtool = os.path.join(str(self.build_dir), "libtool")
        if not os.path.exists(libtool):
          return RCO.ReturnCode("OK", "file libtool not existing '%s'" % libtool)

        with open(libtool, 'r') as lf:
          for line in lf.readlines():
            if 'hack_libtool' in line:
              return RCO.ReturnCode("OK", "existing 'hack_libtool' in '%s'" % libtool)

        # fix libtool by replacing CC="<compil>" with hack_libtool function
        # TODO rewrite that horreur
        obsolete_hack_cmd='''
set -x
sed -i "s%^CC=\\"\(.*\)\\"%hack_libtool() { \\n\\
if test \\"\$(echo \$@ | grep -E '\\\\\\-L/usr/lib(/../lib)?(64)? ')\\" == \\\"\\\" \\n\\
  then\\n\\
    cmd=\\"\\1 \$@\\"\\n\\
  else\\n\\
    cmd=\\"\\1 \\"\`echo \$@ | sed -r -e 's|(.*)-L/usr/lib(/../lib)?(64)? (.*)|\\\\\\1\\\\\\4 -L/usr/lib\\\\\\3|g'\`\\n\\
  fi\\n\\
  \$cmd\\n\\
}\\n\\
CC=\\"hack_libtool\\"%g" libtool'''

        hack_cmd=r'''
set -x
sed -i "s%^CC=\"\(.*\)\"%hack_libtool() { \n\
if test \"\$(echo \$@ | grep -E '\\\-L/usr/lib(/../lib)?(64)? ')\" == \"\" \n\
  then\n\
    cmd=\"\1 \$@\"\n\
  else\n\
    cmd=\"\1 \"\`echo \$@ | sed -r -e 's|(.*)-L/usr/lib(/../lib)?(64)? (.*)|\\\1\\\4 -L/usr/lib\\\3|g'\`\n\
  fi\n\
  \$cmd\n\
}\n\
CC=\"hack_libtool\"%g" libtool
'''

        env = self.build_environ.environ.environ
        res = UTS.Popen(hack_cmd, cwd=str(self.build_dir), env=env)
        return res


    def make(self, nb_proc, make_opt=""):
        """Runs make to build the module."""
        # make
        cmd = """
set -x
make -j %s %s
""" % (nb_proc, make_opt)

        env = self.build_environ.environ.environ
        res = UTS.Popen(cmd, cwd=str(self.build_dir), env=env, logger=self.logger)
        return res

    
    def wmake(self, nb_proc, opt_nb_proc = None):
        """Runs msbuild to build the module."""
        hh = 'MSBUILD /m:%s' % str(nb_proc)
        if self.debug_mode:
            hh += " " + UTS.red("DEBUG")
        # make
        cmd = "msbuild /maxcpucount:%s" % nb_proc
        if self.debug_mode:
            cmd += " /p:Configuration=Debug"
        else:
            cmd += " /p:Configuration=Release"
        cmd += cmd + " ALL_BUILD.vcxproj"

        env = self.build_environ.environ.environ
        res = UTS.Popen(command, cwd=str(self.build_dir), env=env, logger=self.logger)  
        return res
        

    def install(self):
        """Runs 'make install'."""
        if self.config.VARS.dist_name=="Win":
            cmd = "msbuild INSTALL.vcxproj"
            if self.debug_mode:
                cmd += " /p:Configuration=Debug"
            else:
                cmd += " /p:Configuration=Release"
        else :
            cmd = 'make install'

        env = self.build_environ.environ.environ
        res = UTS.Popen(command, cwd=str(self.build_dir), env=env, logger=self.logger)  
        return res

    def check(self, command=""):
        """Runs 'make_check'."""
        if ARCH.is_windows():
            cmd = "msbuild RUN_TESTS.vcxproj"
        else :
            if self.product_info.build_source=="autotools" :
                cmd = 'make check'
            else:
                cmd = 'make test'
        
        if command:
            cmd = command
        
        env = self.build_environ.environ.environ
        res = UTS.Popen(command, cwd=str(self.build_dir), env=env , logger=self.logger) 
        return res

      
    def do_default_build(self,
                         build_conf_options="",
                         configure_options="",
                         show_warning=True):
        """Performs a default build for this module."""
        use_autotools = False
        if 'use_autotools' in self.product_info:
            uc = self.product_info.use_autotools
            if uc in ['always', 'yes']: 
                use_autotools = True
            elif uc == 'option': 
                use_autotools = self.options.autotools


        self.use_autotools = use_autotools

        use_ctest = False
        if 'use_ctest' in self.product_info:
            uc = self.product_info.use_ctest
            if uc in ['always', 'yes']: 
                use_ctest = True
            elif uc == 'option': 
                use_ctest = self.options.ctest

        self.use_ctest = use_ctest

        if show_warning:
            cmd = ""
            if use_autotools: cmd = "(autotools)"
            if use_ctest: cmd = "(ctest)"
            
            self.info("%s: Run default compilation method %s" % (self.module, cmd))

        if use_autotools:
            if not self.prepare(): return self.get_result()
            if not self.build_configure(build_conf_options): return self.get_result()
            if not self.configure(configure_options): return self.get_result()
            if not self.make(): return self.get_result()
            if not self.install(): return self.get_result()
            if not self.clean(): return self.get_result()
           
        else: # CMake
            if self.config.VARS.dist_name=='Win':
                if not self.wprepare(): return self.get_result()
                if not self.cmake(): return self.get_result()
                if not self.wmake(): return self.get_result()
                if not self.install(): return self.get_result()
                if not self.clean(): return self.get_result()
            else :
                if not self.prepare(): return self.get_result()
                if not self.cmake(): return self.get_result()
                if not self.make(): return self.get_result()
                if not self.install(): return self.get_result()
                if not self.clean(): return self.get_result()

        return self.get_result()

    def do_python_script_build(self, script, nb_proc):
        """Performs a build with a script."""
        logger = self.logger
        # script found
        logger.info(_("Compile %s using script %s\n") % \
                          (self.product_info.name, UTS.label(script)) )
        try:
            import imp
            product = self.product_info.name
            pymodule = imp.load_source(product + "_compile_script", script)
            self.nb_proc = nb_proc
            retcode = pymodule.compil(self.config, self, logger)
        except:
            __, exceptionValue, exceptionTraceback = sys.exc_info()
            logger.error(str(exceptionValue))
            import traceback
            traceback.print_tb(exceptionTraceback)
            traceback.print_exc()
            retcode = 1
        finally:
            self.put_txt_log_in_appli_log_dir("script")
        return retcode

    def complete_environment(self, make_options):
        assert self.build_environ is not None
        # pass additional variables to environment 
        # (may be used by the build script)
        self.build_environ.set("SOURCE_DIR", str(self.source_dir))
        self.build_environ.set("INSTALL_DIR", str(self.install_dir))
        self.build_environ.set("PRODUCT_INSTALL", str(self.install_dir))
        self.build_environ.set("BUILD_DIR", str(self.build_dir))
        self.build_environ.set("PRODUCT_BUILD", str(self.build_dir))
        self.build_environ.set("MAKE_OPTIONS", make_options)
        self.build_environ.set("DIST_NAME", self.config.VARS.dist_name)
        self.build_environ.set("DIST_VERSION", self.config.VARS.dist_version)
        self.build_environ.set("DIST", self.config.VARS.dist)
        self.build_environ.set("VERSION", self.product_info.version)

    def do_batch_script_build(self, script, nb_proc):

        if ARCH.is_windows():
            make_options = "/maxcpucount:%s" % nb_proc
        else :
            make_options = "-j%s" % nb_proc

        self.logger.trace(_("Run build script '%s'") % script)
        self.complete_environment(make_options)
        
        # linux or win compatible, have to be chmod +x ?
        cmd = """
# Run build script
%s
""" % script
        
        env = self.build_environ.environ.environ
        res = UTS.Popen(cmd, cwd=str(self.build_dir), env=env)
        return res
    
    def do_script_build(self, script, number_of_proc=0):
        # define make options (may not be used by the script)
        if number_of_proc==0:
            nb_proc = UTS.get_config_key(self.product_info,"nb_proc", 0)
            if nb_proc == 0: 
                nb_proc = self.config.VARS.nb_proc
        else:
            nb_proc = min(number_of_proc, self.config.VARS.nb_proc)
            
        extension = os.path.splitext(script)[-1]
        if extension in [".bat", ".sh", ".bash"]:
            return self.do_batch_script_build(script, nb_proc)
        if extension == ".py":
            return self.do_python_script_build(script, nb_proc)
        
        msg = _("The script %s must have extension as .sh, .bat or .py.") % script
        return RCO.ReturnCode("KO", msg)
        
