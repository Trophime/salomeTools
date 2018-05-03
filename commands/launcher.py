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

import platform
import shutil
import getpass
import subprocess
import stat

import src.debug as DBG
import src.returnCode as RCO
import src.utilsSat as UTS
import src.product as PROD
from src.salomeTools import _BaseCommand
import src.environment as ENVI
import src.fileEnviron as FENV

########################################################################
# Command class
########################################################################
class Command(_BaseCommand):
  """
  The launcher command generates a SALOME launcher.
  
  | examples:
  | >> sat launcher SALOME 
  """
  
  name = "launcher"
  
  def getParser(self):
    """Define all possible options for command 'sat launcher <options>'"""
    parser = self.getParserWithHelp()
    return parser

  def run(self, cmd_arguments):
    """method called for command 'sat launcher <options>'"""
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

    # Verify that the command was called with an application
    UTS.check_config_has_application(config).raiseIfKo()
    
    # Determine the launcher name (from option, profile section or by default "salome")
    if options.name:
        launcher_name = options.name
    else:
        launcher_name = UTS.get_launcher_name(config)

    # set the launcher path
    launcher_path = config.APPLICATION.workdir

    # Copy a catalog if the option is called
    additional_environ = {}
    if options.catalog:
        additional_environ = copy_catalog(config, options.catalog)

    # Generate a catalog of resources if the corresponding option was called
    if options.gencat:
        catalog_path = generate_catalog(options.gencat.split(","), config, logger)
        additional_environ = copy_catalog(config, catalog_path)

    # Generate the launcher
    launcherPath = generate_launch_file( config,
                                         logger,
                                         launcher_name,
                                         launcher_path,
                                         additional_env = additional_environ )

    return 0


def generate_launch_file(config,
                         logger,
                         launcher_name,
                         pathlauncher,
                         display=True,
                         additional_env={}):
    """Generates the launcher file.
    
    :param config: (Config) The global configuration
    :param logger: (Logger) 
      The logger instance to use for the display and logging
    :param launcher_name: (str) The name of the launcher to generate
    :param pathlauncher: (str) The path to the launcher to generate
    :param display: (bool) If False, do not print anything in the terminal
    :param additional_env: (dict) 
      The dict giving additional environment variables
    :return: (str) The launcher file path.
    """
    
    # Compute the default launcher path if it is not provided in pathlauncher
    # parameter
    filepath = os.path.join(pathlauncher, launcher_name)

    # Remove the file if it exists in order to replace it
    if os.path.exists(filepath):
        os.remove(filepath)

    # Add the APPLI variable
    additional_env['APPLI'] = filepath


    # get KERNEL bin installation path 
    # (in order for the launcher to get python salomeContext API)
    kernel_cfg = PROD.get_product_config(config, "KERNEL")
    if not PROD.check_installation(kernel_cfg):
        raise Exception(_("KERNEL is not installed"))
    kernel_root_dir = kernel_cfg.install_dir

    # set kernel bin dir (considering fhs property)
    if UTS.get_property_in_product_cfg(kernel_cfg, "fhs"):
        bin_kernel_install_dir = os.path.join(kernel_root_dir,"bin") 
    else:
        bin_kernel_install_dir = os.path.join(kernel_root_dir,"bin","salome") 

    # Get the launcher template
    withProfile = FENV.withProfile\
      .replace("BIN_KERNEL_INSTALL_DIR", bin_kernel_install_dir)\
      .replace("KERNEL_INSTALL_DIR", kernel_root_dir)

    before, after = withProfile.split(
                                "# here your local standalone environment\n")

    # create an environment file writer
    writer = ENVI.FileEnvWriter(config, logger, pathlauncher, src_root=None, env_info=None)

    # Display some information
    if display:
        # Write the launcher file
        msg = _("Generating launcher for %s :\n  %s\n") % \
              (UTS.label(config.VARS.application), UTS.label(filepath))
        logger.info(msg)
    
    # open the file and write into it
    launch_file = open(filepath, "w")
    launch_file.write(before)
    # Write
    writer.write_cfgForPy_file(launch_file, additional_env=additional_env)
    launch_file.write(after)
    launch_file.close()
    
    # change the rights in order to make the file executable for everybody
    os.chmod(filepath,
             stat.S_IRUSR |
             stat.S_IRGRP |
             stat.S_IROTH |
             stat.S_IWUSR |
             stat.S_IXUSR |
             stat.S_IXGRP |
             stat.S_IXOTH)
    return filepath


def generate_catalog(machines, config, logger):
    """Generates an xml catalog file from a list of machines.
    
    :param machines: (list) The list of machines to add in the catalog   
    :param config: (Config) The global configuration
    :param logger: (Logger) 
      The logger instance to use for the display and logging
    :return: (str) The catalog file path.
    """
    # remove empty machines
    machines = map(lambda l: l.strip(), machines)
    machines = filter(lambda l: len(l) > 0, machines)
    
    # log something
    logger.debug("  %s = %s\n" % \
                 (_("Generate Resources Catalog"), ", ".join(machines)) )
    
    # The command to execute on each machine in order to get some information
    cmd = '"cat /proc/cpuinfo | grep MHz ; cat /proc/meminfo | grep MemTotal"'
    user = getpass.getuser()

    # Create the catalog path
    catfile = UTS.get_tmp_filename(config, "CatalogResources.xml")
    catalog = file(catfile, "w")
    
    # Write into it
    catalog.write("<!DOCTYPE ResourcesCatalog>\n<resources>\n")
    for k in machines:
        logger.debug("    ssh %s " % (k + " ").ljust(20, '.'))

        # Verify that the machine is accessible
        ssh_cmd = 'ssh -o "StrictHostKeyChecking no" %s %s' % (k, cmd)
        p = subprocess.Popen(ssh_cmd, shell=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        p.wait()

        if p.returncode != 0: # The machine is not accessible
            logger.error("<KO>: The machine %s is not accessible:\n%s\n" % k + 
                         UTS.red(p.stderr.read()))
        else:
            # The machine is accessible, write the corresponding section on
            # the xml file
            logger.debug("<OK>: The machine %s is accessible:\n" % k)
            lines = p.stdout.readlines()
            freq = lines[0][:-1].split(':')[-1].split('.')[0].strip()
            nb_proc = len(lines) -1
            memory = lines[-1].split(':')[-1].split()[0].strip()
            memory = int(memory) / 1000

            catalog.write("    <machine\n")
            catalog.write("        protocol=\"ssh\"\n")
            catalog.write("        nbOfNodes=\"1\"\n")
            catalog.write("        mode=\"interactif\"\n")
            catalog.write("        OS=\"LINUX\"\n")
            catalog.write("        CPUFreqMHz=\"%s\"\n" % freq)
            catalog.write("        nbOfProcPerNode=\"%s\"\n" % nb_proc)
            catalog.write("        memInMB=\"%s\"\n" % memory)
            catalog.write("        userName=\"%s\"\n" % user)
            catalog.write("        name=\"%s\"\n" % k)
            catalog.write("        hostname=\"%s\"\n" % k)
            catalog.write("    >\n")
            catalog.write("    </machine>\n")

    catalog.write("</resources>\n")
    catalog.close()
    return catfile

def copy_catalog(config, catalog_path):
    """Copy the xml catalog file into the right location
    
    :param config: (Config) The global configuration
    :param catalog_path: (str) the catalog file path
    :return: (dict) 
      The environment dictionary corresponding to the file path.
    """
    # Verify the existence of the file
    if not os.path.exists(catalog_path):
        raise IOError(_("Catalog not found: %s") % catalog_path)
    # Get the application directory and copy catalog inside
    out_dir = config.APPLICATION.workdir
    new_catalog_path = os.path.join(out_dir, "CatalogResources.xml")
    # Do the copy
    shutil.copy(catalog_path, new_catalog_path)
    additional_environ = {'USER_CATALOG_RESOURCES_FILE' : new_catalog_path}
    return additional_environ
