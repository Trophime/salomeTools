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
import stat
import shutil
import datetime
import tarfile
import codecs
import string
import traceback

from commands.application import get_SALOME_modules

import src.debug as DBG
import src.returnCode as RCO
import src.utilsSat as UTS
from src.salomeTools import _BaseCommand
import src.pyconf as PYCONF
import src.utilsSat as UTS

BINARY = "binary"
SOURCE = "Source"
PROJECT = "Project"
SAT = "Sat"

ARCHIVE_DIR = "ARCHIVES"
PROJECT_DIR = "PROJECT"

IGNORED_DIRS = [".git", ".svn"]
IGNORED_EXTENSIONS = []

PROJECT_TEMPLATE = """\
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# The path to the archive root directory
root_path : $PWD + "/../"
# path to the PROJECT
project_path : $PWD + "/"

# Where to search the archives of the products
ARCHIVEPATH : $root_path + "ARCHIVES"
# Where to search the pyconf of the applications
APPLICATIONPATH : $project_path + "applications/"
# Where to search the pyconf of the products
PRODUCTPATH : $project_path + "products/"
# Where to search the pyconf of the jobs of the project
JOBPATH : $project_path + "jobs/"
# Where to search the pyconf of the machines of the project
MACHINEPATH : $project_path + "machines/"
"""

LOCAL_TEMPLATE = ("""\
#!/usr/bin/env python
#-*- coding:utf-8 -*-

  LOCAL :
  {
    base : 'default'
    workdir : 'default'
    log_dir : 'default'
    archive_dir : 'default'
    VCS : None
    tag : None
  }

PROJECTS :
{
project_file_paths : [$VARS.salometoolsway + $VARS.sep + \"..\" + $VARS.sep"""
""" + \"""" + PROJECT_DIR + """\" + $VARS.sep + "project.pyconf"]
}
""")
  

########################################################################
# Command class
########################################################################
class Command(_BaseCommand):
  """\
  The package command creates an archive.
  There are 4 kinds of archive, which can be mixed:
    1- The binary archive. It contains all the product installation directories and a launcher.
    2- The sources archive. It contains the products archives, 
       a project corresponding to the application and salomeTools.
    3- The project archive. It contains a project (give the project file path as argument).
    4- The salomeTools archive. It contains salomeTools.
  
  examples:
    >> sat package SALOME --binaries --sources
  """
  
  name = "package"
  
  def getParser(self):
    """Define all options for command 'sat package <options>'"""
    parser = self.getParserWithHelp()
    parser.add_option('b', 'binaries', 'boolean', 'binaries',
        _('Optional: Produce a binary package.'), False)
    parser.add_option('f', 'force_creation', 'boolean', 'force_creation',
        _('Optional: Only binary package: produce the archive even if '
          'there are some missing products.'), False)
    parser.add_option('s', 'sources', 'boolean', 'sources',
        _('Optional: Produce a compilable archive of the sources of the '
          'application.'), False)
    parser.add_option('', 'with_vcs', 'boolean', 'with_vcs',
        _('Optional: Only source package: do not make archive of vcs products.'),
        False)
    parser.add_option('p', 'project', 'string', 'project',
        _('Optional: Produce an archive that contains a project.'), "")
    parser.add_option('t', 'salometools', 'boolean', 'sat',
        _('Optional: Produce an archive that contains salomeTools.'), False)
    parser.add_option('n', 'name', 'string', 'name',
        _('Optional: The name or full path of the archive.'), None)
    parser.add_option('', 'add_files', 'list2', 'add_files',
        _('Optional: The list of additional files to add to the archive.'), [])
    parser.add_option('', 'without_commercial', 'boolean', 'without_commercial',
        _('Optional: do not add commercial licence.'), False)
    parser.add_option('', 'without_property', 'string', 'without_property',
        _('Optional: Filter the products by their properties.\n'
          '\tSyntax: --without_property <property>:<value>'))
    return parser

  def run(self, cmd_arguments):
    """method called for command 'sat package <options>'"""
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
       
    # Check that a type of package is called, and only one
    all_option_types = (options.binaries,
                        options.sources,
                        options.project not in ["", None],
                        options.sat)

    # Check if no option for package type
    if all_option_types.count(True) == 0:
        msg = _("""\
Needs a type for the package
Use one of the following options:
  '--binaries' '--sources' '--project' or '--salometools'\n""")
        logger.error(msg)
        return 1
    
    # The repository where to put the package if not Binary or Source
    package_default_path = config.LOCAL.workdir
    
    # if the package contains binaries or sources:
    if options.binaries or options.sources:
        # Check that the command has been called with an application
        src.check_config_has_application(config)

        # Display information
        logger.info(_("Packaging application %s\n") % \
            UTS.label(config.VARS.application), 1)
        
        # Get the default directory where to put the packages
        package_default_path = os.path.join(config.APPLICATION.workdir, "PACKAGE")
        UTS.ensure_path_exists(package_default_path)
        
    # if the package contains a project:
    if options.project:
        # check that the project is visible by SAT
        if options.project not in config.PROJECTS.project_file_paths:
            local_path = os.path.join(
                   config.VARS.salometoolsway, "data", "local.pyconf")
            msg = _("""\
The project %s is not visible by salomeTools.
Please add it in the %s file.\n""") % (options.project, local_path)
            logger.error(msg)
            return 1
    
    # Remove the products that are filtered by the --without_property option
    if options.without_property:
        [prop, value] = options.without_property.split(":")
        update_config(config, prop, value)
    
    # get the name of the archive or build it
    if options.name:
        if os.path.basename(options.name) == options.name:
            # only a name (not a path)
            archive_name = options.name           
            dir_name = package_default_path
        else:
            archive_name = os.path.basename(options.name)
            dir_name = os.path.dirname(options.name)
        
        # suppress extension
        if archive_name[-len(".tgz"):] == ".tgz":
            archive_name = archive_name[:-len(".tgz")]
        if archive_name[-len(".tar.gz"):] == ".tar.gz":
            archive_name = archive_name[:-len(".tar.gz")]
        
    else:
        archive_name=""
        dir_name = package_default_path
        if options.binaries or options.sources:
            archive_name = config.APPLICATION.name

        if options.binaries:
            archive_name += "-"+config.VARS.dist
            
        if options.sources:
            archive_name += "-SRC"
            if options.with_vcs:
                archive_name += "-VCS"

        if options.project:
            project_name, __ = os.path.splitext(
                                            os.path.basename(options.project))
            archive_name += ("PROJECT-" + project_name)
 
        if options.sat:
            archive_name += ("salomeTools_" + config.INTERNAL.sat_version)
        if len(archive_name)==0: # no option worked 
            msg = _("""\
Cannot name the archive.
check if at least one of the following options was selected: 
  '--binaries' '--sources' '--project' or '--salometools'\n""")
            logger.error(msg)
            return 1
 
    path_targz = os.path.join(dir_name, archive_name + ".tgz")
    
    logger.info("  Package path = %s\n" UTS.blue(path_targz))

    # Create a working directory for all files that are produced during the
    # package creation and that will be removed at the end of the command
    tmp_working_dir = os.path.join(config.VARS.tmp_root, config.VARS.datehour)
    UTS.ensure_path_exists(tmp_working_dir)
    logger.debug(_("The temporary working directory: %s\n") % tmp_working_dir)
    
    msg = _("Preparation of files to add to the archive")
    logger.info(UTS.label(msg))

    d_files_to_add={}  # content of the archive

    # a dict to hold paths that will need to be substitute for users recompilations
    d_paths_to_substitute={}  

    if options.binaries:
        d_bin_files_to_add = binary_package(config, logger, options, tmp_working_dir)
        # for all binaries dir, store the substitution that will be required 
        # for extra compilations
        for key in d_bin_files_to_add:
            if key.endswith("(bin)"):
                source_dir = d_bin_files_to_add[key][0]
                path_in_archive = d_bin_files_to_add[key][1].replace("BINARIES-" + config.VARS.dist,"INSTALL")
                if os.path.basename(source_dir)==os.path.basename(path_in_archive):
                    # if basename is the same we will just substitute the dirname 
                    d_paths_to_substitute[os.path.dirname(source_dir)]=\
                        os.path.dirname(path_in_archive)
                else:
                    d_paths_to_substitute[source_dir]=path_in_archive

        d_files_to_add.update(d_bin_files_to_add)

    if options.sources:
        d_files_to_add.update(source_package(runner,
                                        config,
                                        logger, 
                                        options,
                                        tmp_working_dir))
        if options.binaries:
            # for archives with bin and sources we provide a shell script able to 
            # install binaries for compilation
            file_install_bin=produce_install_bin_file(config,logger,
                                                      tmp_working_dir,
                                                      d_paths_to_substitute,
                                                      "install_bin.sh")
            d_files_to_add.update({"install_bin" : (file_install_bin, "install_bin.sh")})
            logger.debug("substitutions to be done later:\n%s\n" % str(d_paths_to_substitute))

    else:
        # --salomeTool option is not considered when --sources is selected, as this option
        # already brings salomeTool!
        if options.sat:
            d_files_to_add.update({"salomeTools" : (config.VARS.salometoolsway, "")})
        
    
    if options.project:
        d_files_to_add.update(project_package(options.project, tmp_working_dir))

    if not(d_files_to_add):
        msg = _("Empty dictionary to build the archive.\n")
        logger.error(msg)
        return 1

    # Add the README file in the package
    local_readme_tmp_path = add_readme(config, options, tmp_working_dir)
    d_files_to_add["README"] = (local_readme_tmp_path, "README")

    # Add the additional files of option add_files
    if options.add_files:
        for file_path in options.add_files:
            if not os.path.exists(file_path):
                msg = _("The file %s is not accessible.\n") % file_path
                continue
            file_name = os.path.basename(file_path)
            d_files_to_add[file_name] = (file_path, file_name)

    msg = UTS.label(_("Actually do the package"))
    logger.info("\n%s\n" % msg)
    
    try:
        # Creating the object tarfile
        tar = tarfile.open(path_targz, mode='w:gz')
        
        # get the filtering function if needed
        filter_function = exclude_VCS_and_extensions

        # Add the files to the tarfile object
        res = add_files(tar, archive_name, d_files_to_add, logger, f_exclude=filter_function)
        tar.close()
        
    except KeyboardInterrupt:
        logger.critical(UTS.red(_("KeyboardInterrupt forced interruption\n"))
        logger.info(_("Removing the temporary working directory ... "))
        # remove the working directory
        shutil.rmtree(tmp_working_dir)
        logger.info("<OK>")
        return 1
    
    # remove the working directory    
    shutil.rmtree(tmp_working_dir)
    
    # Print again the path of the package
    logger.info("  Package path = %s\n" UTS.blue(path_targz))
    
    return res


def add_files(tar, name_archive, d_content, logger, f_exclude=None):
    """\
    Create an archive containing all directories and files that are given 
    in the d_content argument.
    
    :param tar tarfile: The tarfile instance used to make the archive.
    :param name_archive str: The name of the archive to make.
    :param d_content dict: The dictionary that contain all directories and files
                           to add in the archive.
                           d_content[label] = 
                                        (path_on_local_machine, path_in_archive)
    :param logger Logger: the logging instance
    :param f_exclude Function: the function that filters
    :return: 0 if success, 1 if not.
    :rtype: int
    """
    # get the max length of the messages in order to make the display
    max_len = len(max(d_content.keys(), key=len))
    
    success = 0
    # loop over each directory or file stored in the d_content dictionary
    for name in d_content.keys():
        # display information
        len_points = max_len - len(name)
        logger.info(name + " " + len_points * "." + " ")
        # Get the local path and the path in archive 
        # of the directory or file to add
        local_path, archive_path = d_content[name]
        in_archive = os.path.join(name_archive, archive_path)
        # Add it in the archive
        try:
            tar.add(local_path, arcname=in_archive, exclude=f_exclude)
            logger.info("<OK>\n")
        except Exception as e:
            logger.info("<KO> %s\n" str(e))
            success = 1
    return success

def exclude_VCS_and_extensions(filename):
    """\
    The function that is used to exclude from package the link to the 
    VCS repositories (like .git)

    :param filename Str: The filname to exclude (or not).
    :return: True if the file has to be exclude
    :rtype: Boolean
    """
    for dir_name in IGNORED_DIRS:
        if dir_name in filename:
            return True
    for extension in IGNORED_EXTENSIONS:
        if filename.endswith(extension):
            return True
    return False

def produce_relative_launcher(config,
                              logger,
                              file_dir,
                              file_name,
                              binaries_dir_name,
                              with_commercial=True):
    '''Create a specific SALOME launcher for the binary package. This launcher 
       uses relative paths.
    
    :param config Config: The global configuration.
    :param logger Logger: the logging instance
    :param file_dir str: the directory where to put the launcher
    :param file_name str: The launcher name
    :param binaries_dir_name str: the name of the repository where the binaries
                                  are, in the archive.
    :return: the path of the produced launcher
    :rtype: str
    '''
    
    # get KERNEL installation path 
    kernel_root_dir = os.path.join(binaries_dir_name, "KERNEL")

    # set kernel bin dir (considering fhs property)
    kernel_cfg = src.product.get_product_config(config, "KERNEL")
    if src.get_property_in_product_cfg(kernel_cfg, "fhs"):
        bin_kernel_install_dir = os.path.join(kernel_root_dir,"bin") 
    else:
        bin_kernel_install_dir = os.path.join(kernel_root_dir,"bin","salome") 

    # Get the launcher template and do substitutions
    withProfile = src.fileEnviron.withProfile

    withProfile = withProfile.replace(
        "ABSOLUTE_APPLI_PATH'] = 'KERNEL_INSTALL_DIR'",
        "ABSOLUTE_APPLI_PATH'] = out_dir_Path + '" + config.VARS.sep + kernel_root_dir + "'")
    withProfile = withProfile.replace(
        " 'BIN_KERNEL_INSTALL_DIR'",
        " out_dir_Path + '" + config.VARS.sep + bin_kernel_install_dir + "'")

    before, after = withProfile.split(
                                "# here your local standalone environment\n")

    # create an environment file writer
    writer = src.environment.FileEnvWriter(config,
                                           logger,
                                           file_dir,
                                           src_root=None)
    
    filepath = os.path.join(file_dir, file_name)
    # open the file and write into it
    launch_file = open(filepath, "w")
    launch_file.write(before)
    # Write
    writer.write_cfgForPy_file(launch_file,
                               for_package = binaries_dir_name,
                               with_commercial=with_commercial)
    launch_file.write(after)
    launch_file.close()
    
    # Little hack to put out_dir_Path outside the strings
    src.replace_in_file(filepath, 'r"out_dir_Path', 'out_dir_Path + r"' )
    
    # A hack to put a call to a file for distene licence.
    # It does nothing to an application that has no distene product
    hack_for_distene_licence(filepath)
       
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

def hack_for_distene_licence(filepath):
    '''Replace the distene licence env variable by a call to a file.
    
    :param filepath Str: The path to the launcher to modify.
    '''  
    shutil.move(filepath, filepath + "_old")
    fileout= filepath
    filein = filepath + "_old"
    fin = open(filein, "r")
    fout = open(fileout, "w")
    text = fin.readlines()
    # Find the Distene section
    num_line = -1
    for i,line in enumerate(text):
        if "# Set DISTENE License" in line:
            num_line = i
            break
    if num_line == -1:
        # No distene product, there is nothing to do
        fin.close()
        for line in text:
            fout.write(line)
        fout.close()
        return
    del text[num_line +1]
    del text[num_line +1]
    text_to_insert ="""\
    import imp
    try:
        distene = imp.load_source('distene_licence', '/data/tmpsalome/salome/prerequis/install/LICENSE/dlim8.var.py')
        distene.set_distene_variables(context)
    except:
        pass
"""
    text.insert(num_line + 1, text_to_insert)
    for line in text:
        fout.write(line)
    fin.close()    
    fout.close()
    return
    
def produce_relative_env_files(config,
                              logger,
                              file_dir,
                              binaries_dir_name):
    '''Create some specific environment files for the binary package. These 
       files use relative paths.
    
    :param config Config: The global configuration.
    :param logger Logger: the logging instance
    :param file_dir str: the directory where to put the files
    :param binaries_dir_name str: the name of the repository where the binaries
                                  are, in the archive.
    :return: the list of path of the produced environment files
    :rtype: List
    '''  
    # create an environment file writer
    writer = src.environment.FileEnvWriter(config,
                                           logger,
                                           file_dir,
                                           src_root=None)
    
    # Write
    filepath = writer.write_env_file("env_launch.sh",
                          False, # for launch
                          "bash",
                          for_package = binaries_dir_name)

    # Little hack to put out_dir_Path as environment variable
    src.replace_in_file(filepath, '"out_dir_Path', '"${out_dir_Path}' )

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

def produce_install_bin_file(config,
                             logger,
                             file_dir,
                             d_sub,
                             file_name):
    '''Create a bash shell script which do substitutions in BIRARIES dir 
       in order to use it for extra compilations.
    
    :param config Config: The global configuration.
    :param logger Logger: the logging instance
    :param file_dir str: the directory where to put the files
    :param d_sub, dict: the dictionnary that contains the substitutions to be done
    :param file_name str: the name of the install script file
    :return: the produced file
    :rtype: str
    '''  
    # Write
    filepath = os.path.join(file_dir, file_name)
    # open the file and write into it
    # use codec utf-8 as sat variables are in unicode
    with codecs.open(filepath, "w", 'utf-8') as installbin_file:
        installbin_template_path = os.path.join(config.VARS.internal_dir,
                                        "INSTALL_BIN.template")
        
        # build the name of the directory that will contain the binaries
        binaries_dir_name = "BINARIES-" + config.VARS.dist
        # build the substitution loop
        loop_cmd = "for f in $(grep -RIl"
        for key in d_sub:
            loop_cmd += " -e "+ key
        loop_cmd += ' INSTALL); do\n     sed -i "\n'
        for key in d_sub:
            loop_cmd += "        s?" + key + "?$(pwd)/" + d_sub[key] + "?g\n"
        loop_cmd += '            " $f\ndone'

        d={}
        d["BINARIES_DIR"] = binaries_dir_name
        d["SUBSTITUTION_LOOP"]=loop_cmd
        
        # substitute the template and write it in file
        content=src.template.substitute(installbin_template_path, d)
        installbin_file.write(content)
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

def product_appli_creation_script(config,
                                  logger,
                                  file_dir,
                                  binaries_dir_name):
    '''Create a script that can produce an application (EDF style) in the binary
       package.
    
    :param config Config: The global configuration.
    :param logger Logger: the logging instance
    :param file_dir str: the directory where to put the file
    :param binaries_dir_name str: the name of the repository where the binaries
                                  are, in the archive.
    :return: the path of the produced script file
    :rtype: Str
    '''
    template_name = "create_appli.py.for_bin_packages.template"
    template_path = os.path.join(config.VARS.internal_dir, template_name)
    text_to_fill = open(template_path, "r").read()
    text_to_fill = text_to_fill.replace("TO BE FILLED 1",
                                        '"' + binaries_dir_name + '"')
    
    text_to_add = ""
    for product_name in get_SALOME_modules(config):
        product_info = src.product.get_product_config(config, product_name)
       
        if src.product.product_is_smesh_plugin(product_info):
            continue

        if 'install_dir' in product_info and bool(product_info.install_dir):
            if src.product.product_is_cpp(product_info):
                # cpp module
                for cpp_name in src.product.get_product_components(product_info):
                    line_to_add = ("<module name=\"" + 
                                   cpp_name + 
                                   "\" gui=\"yes\" path=\"''' + "
                                   "os.path.join(dir_bin_name, \"" + 
                                   cpp_name + "\") + '''\"/>")
            else:
                # regular module
                line_to_add = ("<module name=\"" + 
                               product_name + 
                               "\" gui=\"yes\" path=\"''' + "
                               "os.path.join(dir_bin_name, \"" + 
                               product_name + "\") + '''\"/>")
            text_to_add += line_to_add + "\n"
    
    filled_text = text_to_fill.replace("TO BE FILLED 2", text_to_add)
    
    tmp_file_path = os.path.join(file_dir, "create_appli.py")
    ff = open(tmp_file_path, "w")
    ff.write(filled_text)
    ff.close()
    
    # change the rights in order to make the file executable for everybody
    os.chmod(tmp_file_path,
             stat.S_IRUSR |
             stat.S_IRGRP |
             stat.S_IROTH |
             stat.S_IWUSR |
             stat.S_IXUSR |
             stat.S_IXGRP |
             stat.S_IXOTH)
    
    return tmp_file_path

def binary_package(config, logger, options, tmp_working_dir):
    '''Prepare a dictionary that stores all the needed directories and files to
       add in a binary package.
    
    :param config Config: The global configuration.
    :param logger Logger: the logging instance
    :param options OptResult: the options of the launched command
    :param tmp_working_dir str: The temporary local directory containing some 
                                specific directories or files needed in the 
                                binary package
    :return: the dictionary that stores all the needed directories and files to
             add in a binary package.
             {label : (path_on_local_machine, path_in_archive)}
    :rtype: dict
    '''

    # Get the list of product installation to add to the archive
    l_products_name = config.APPLICATION.products.keys()
    l_product_info = src.product.get_products_infos(l_products_name,
                                                    config)
    l_install_dir = []
    l_source_dir = []
    l_not_installed = []
    l_sources_not_present = []
    for prod_name, prod_info in l_product_info:

        # Add the sources of the products that have the property 
        # sources_in_package : "yes"
        if src.get_property_in_product_cfg(prod_info,
                                           "sources_in_package") == "yes":
            if os.path.exists(prod_info.source_dir):
                l_source_dir.append((prod_name, prod_info.source_dir))
            else:
                l_sources_not_present.append(prod_name)

        # ignore the native and fixed products for install directories
        if (src.product.product_is_native(prod_info) 
                or src.product.product_is_fixed(prod_info)
                or not src.product.product_compiles(prod_info)):
            continue
        if src.product.check_installation(prod_info):
            l_install_dir.append((prod_name, prod_info.install_dir))
        else:
            l_not_installed.append(prod_name)
        
        # Add also the cpp generated modules (if any)
        if src.product.product_is_cpp(prod_info):
            # cpp module
            for name_cpp in src.product.get_product_components(prod_info):
                install_dir = os.path.join(config.APPLICATION.workdir,
                                           "INSTALL", name_cpp) 
                if os.path.exists(install_dir):
                    l_install_dir.append((name_cpp, install_dir))
                else:
                    l_not_installed.append(name_cpp)
        
    # Print warning or error if there are some missing products
    if len(l_not_installed) > 0:
        text_missing_prods = ""
        for p_name in l_not_installed:
            text_missing_prods += "-" + p_name + "\n"
        
        msg = _("There are missing products installations:\n")
        logger.warning(msg + text_missing_prods))
        if not options.force_creation:
            return None

    # Do the same for sources
    if len(l_sources_not_present) > 0:
        text_missing_prods = ""
        for p_name in l_sources_not_present:
            text_missing_prods += "-" + p_name + "\n"
            
        msg = _("There are missing products sources:\n")
        logger.warning(msg + text_missing_prods)
        if not options.force_creation:
            return None
 
    # construct the name of the directory that will contain the binaries
    binaries_dir_name = "BINARIES-" + config.VARS.dist
    
    # construct the correlation table between the product names, there 
    # actual install directories and there install directory in archive
    d_products = {}
    for prod_name, install_dir in l_install_dir:
        path_in_archive = os.path.join(binaries_dir_name, prod_name)
        d_products[prod_name + " (bin)"] = (install_dir, path_in_archive)
        
    for prod_name, source_dir in l_source_dir:
        path_in_archive = os.path.join("SOURCES", prod_name)
        d_products[prod_name + " (sources)"] = (source_dir, path_in_archive)

    # for packages of SALOME applications including KERNEL, 
    # we produce a salome launcher or a virtual application (depending on salome version)
    if 'KERNEL' in config.APPLICATION.products:
        VersionSalome = src.get_salome_version(config)
        # Case where SALOME has the launcher that uses the SalomeContext API
        if VersionSalome >= 730:
            # create the relative launcher and add it to the files to add
            launcher_name = src.get_launcher_name(config)
            launcher_package = produce_relative_launcher(config,
                                                 logger,
                                                 tmp_working_dir,
                                                 launcher_name,
                                                 binaries_dir_name,
                                                 not(options.without_commercial))
        
            d_products["launcher"] = (launcher_package, launcher_name)
            if options.sources:
                # if we mix binaries and sources, we add a copy of the launcher, 
                # prefixed  with "bin",in order to avoid clashes
                d_products["launcher (copy)"] = (launcher_package, "bin"+launcher_name)
        else:
            # Provide a script for the creation of an application EDF style
            appli_script = product_appli_creation_script(config,
                                                        logger,
                                                        tmp_working_dir,
                                                        binaries_dir_name)
            
            d_products["appli script"] = (appli_script, "create_appli.py")

    # Put also the environment file
    env_file = produce_relative_env_files(config,
                                           logger,
                                           tmp_working_dir,
                                           binaries_dir_name)

    d_products["environment file"] = (env_file, "env_launch.sh")
      
    return d_products

def source_package(sat, config, logger, options, tmp_working_dir):
    '''Prepare a dictionary that stores all the needed directories and files to
       add in a source package.
    
    :param config Config: The global configuration.
    :param logger Logger: the logging instance
    :param options OptResult: the options of the launched command
    :param tmp_working_dir str: The temporary local directory containing some 
                                specific directories or files needed in the 
                                binary package
    :return: the dictionary that stores all the needed directories and files to
             add in a source package.
             {label : (path_on_local_machine, path_in_archive)}
    :rtype: dict
    '''
    
    # Get all the products that are prepared using an archive
    logger.info("Find archive products ... ")
    d_archives, l_pinfo_vcs = get_archives(config, logger)
    logger.info("Done\n")
    d_archives_vcs = {}
    if not options.with_vcs and len(l_pinfo_vcs) > 0:
        # Make archives with the products that are not prepared using an archive
        # (git, cvs, svn, etc)
        logger.info("Construct archives for vcs products ... ")
        d_archives_vcs = get_archives_vcs(l_pinfo_vcs,
                                          sat,
                                          config,
                                          logger,
                                          tmp_working_dir)
        logger.info("Done\n")

    # Create a project
    logger.info("Create the project ... ")
    d_project = create_project_for_src_package(config, tmp_working_dir, options.with_vcs)
    logger.info("Done\n")
    
    # Add salomeTools
    tmp_sat = add_salomeTools(config, tmp_working_dir)
    d_sat = {"salomeTools" : (tmp_sat, "salomeTools")}
    
    # Add a sat symbolic link if not win
    if not src.architecture.is_windows():
        tmp_satlink_path = os.path.join(tmp_working_dir, 'sat')
        try:
            t = os.getcwd()
        except:
            # In the jobs, os.getcwd() can fail
            t = config.LOCAL.workdir
        os.chdir(tmp_working_dir)
        if os.path.lexists(tmp_satlink_path):
            os.remove(tmp_satlink_path)
        os.symlink(os.path.join('salomeTools', 'sat'), 'sat')
        os.chdir(t)
        
        d_sat["sat link"] = (tmp_satlink_path, "sat")
    
    d_source = src.merge_dicts(d_archives, d_archives_vcs, d_project, d_sat)
    return d_source

def get_archives(config, logger):
    '''Find all the products that are get using an archive and all the products
       that are get using a vcs (git, cvs, svn) repository.
    
    :param config Config: The global configuration.
    :param logger Logger: the logging instance
    :return: the dictionary {name_product : 
             (local path of its archive, path in the package of its archive )}
             and the list of specific configuration corresponding to the vcs 
             products
    :rtype: (Dict, List)
    '''
    # Get the list of product informations
    l_products_name = config.APPLICATION.products.keys()
    l_product_info = src.product.get_products_infos(l_products_name,
                                                    config)
    d_archives = {}
    l_pinfo_vcs = []
    for p_name, p_info in l_product_info:
        # ignore the native and fixed products
        if (src.product.product_is_native(p_info) 
                or src.product.product_is_fixed(p_info)):
            continue
        if p_info.get_source == "archive":
            archive_path = p_info.archive_info.archive_name
            archive_name = os.path.basename(archive_path)
        else:
            l_pinfo_vcs.append((p_name, p_info))
            
        d_archives[p_name] = (archive_path,
                              os.path.join(ARCHIVE_DIR, archive_name))
    return d_archives, l_pinfo_vcs

def add_salomeTools(config, tmp_working_dir):
    '''Prepare a version of salomeTools that has a specific local.pyconf file 
       configured for a source package.

    :param config Config: The global configuration.
    :param tmp_working_dir str: The temporary local directory containing some 
                                specific directories or files needed in the 
                                source package
    :return: The path to the local salomeTools directory to add in the package
    :rtype: str
    '''
    # Copy sat in the temporary working directory
    sat_tmp_path = src.Path(os.path.join(tmp_working_dir, "salomeTools"))
    sat_running_path = src.Path(config.VARS.salometoolsway)
    sat_running_path.copy(sat_tmp_path)
    
    # Update the local.pyconf file that contains the path to the project
    local_pyconf_name = "local.pyconf"
    local_pyconf_dir = os.path.join(tmp_working_dir, "salomeTools", "data")
    local_pyconf_file = os.path.join(local_pyconf_dir, local_pyconf_name)
    # Remove the .pyconf file in the root directory of salomeTools if there is
    # any. (For example when launching jobs, a pyconf file describing the jobs 
    # can be here and is not useful) 
    files_or_dir_SAT = os.listdir(os.path.join(tmp_working_dir, "salomeTools"))
    for file_or_dir in files_or_dir_SAT:
        if file_or_dir.endswith(".pyconf") or file_or_dir.endswith(".txt"):
            file_path = os.path.join(tmp_working_dir,
                                     "salomeTools",
                                     file_or_dir)
            os.remove(file_path)
    
    ff = open(local_pyconf_file, "w")
    ff.write(LOCAL_TEMPLATE)
    ff.close()
    
    return sat_tmp_path.path

def get_archives_vcs(l_pinfo_vcs, sat, config, logger, tmp_working_dir):
    '''For sources package that require that all products are get using an 
       archive, one has to create some archive for the vcs products.
       So this method calls the clean and source command of sat and then create
       the archives.

    :param l_pinfo_vcs List: The list of specific configuration corresponding to
                             each vcs product
    :param sat Sat: The Sat instance that can be called to clean and source the
                    products
    :param config Config: The global configuration.
    :param logger Logger: the logging instance
    :param tmp_working_dir str: The temporary local directory containing some 
                                specific directories or files needed in the 
                                source package
    :return: the dictionary that stores all the archives to add in the source 
             package. {label : (path_on_local_machine, path_in_archive)}
    :rtype: dict
    '''
    # clean the source directory of all the vcs products, then use the source 
    # command and thus construct an archive that will not contain the patches
    l_prod_names = [pn for pn, __ in l_pinfo_vcs]
    # clean
    logger.info(_("clean sources\n"))
    args_clean = config.VARS.application
    args_clean += " --sources --products "
    args_clean += ",".join(l_prod_names)
    sat.clean(args_clean, batch=True, verbose=0, logger_add_link = logger)
    # source
    logger.info(_("get sources"))
    args_source = config.VARS.application
    args_source += " --products "
    args_source += ",".join(l_prod_names)
    sat.source(args_source, batch=True, verbose=0, logger_add_link = logger)

    # make the new archives
    d_archives_vcs = {}
    for pn, pinfo in l_pinfo_vcs:
        path_archive = make_archive(pn, pinfo, tmp_working_dir)
        d_archives_vcs[pn] = (path_archive,
                              os.path.join(ARCHIVE_DIR, pn + ".tgz"))
    return d_archives_vcs

def make_archive(prod_name, prod_info, where):
    '''Create an archive of a product by searching its source directory.

    :param prod_name str: The name of the product.
    :param prod_info Config: The specific configuration corresponding to the 
                             product
    :param where str: The path of the repository where to put the resulting 
                      archive
    :return: The path of the resulting archive
    :rtype: str
    '''
    path_targz_prod = os.path.join(where, prod_name + ".tgz")
    tar_prod = tarfile.open(path_targz_prod, mode='w:gz')
    local_path = prod_info.source_dir
    tar_prod.add(local_path,
                 arcname=prod_name,
                 exclude=exclude_VCS_and_extensions)
    tar_prod.close()
    return path_targz_prod       

def create_project_for_src_package(config, tmp_working_dir, with_vcs):
    '''Create a specific project for a source package.

    :param config Config: The global configuration.
    :param tmp_working_dir str: The temporary local directory containing some 
                                specific directories or files needed in the 
                                source package
    :param with_vcs boolean: True if the package is with vcs products (not 
                             transformed into archive products)
    :return: The dictionary 
             {"project" : (produced project, project path in the archive)}
    :rtype: Dict
    '''

    # Create in the working temporary directory the full project tree
    project_tmp_dir = os.path.join(tmp_working_dir, PROJECT_DIR)
    products_pyconf_tmp_dir = os.path.join(project_tmp_dir,
                                         "products")
    compil_scripts_tmp_dir = os.path.join(project_tmp_dir,
                                         "products",
                                         "compil_scripts")
    env_scripts_tmp_dir = os.path.join(project_tmp_dir,
                                         "products",
                                         "env_scripts")
    patches_tmp_dir = os.path.join(project_tmp_dir,
                                         "products",
                                         "patches")
    application_tmp_dir = os.path.join(project_tmp_dir,
                                         "applications")
    for directory in [project_tmp_dir,
                      compil_scripts_tmp_dir,
                      env_scripts_tmp_dir,
                      patches_tmp_dir,
                      application_tmp_dir]:
        UTS.ensure_path_exists(directory)

    # Create the pyconf that contains the information of the project
    project_pyconf_name = "project.pyconf"        
    project_pyconf_file = os.path.join(project_tmp_dir, project_pyconf_name)
    ff = open(project_pyconf_file, "w")
    ff.write(PROJECT_TEMPLATE)
    ff.close()
    
    # Loop over the products to get there pyconf and all the scripts 
    # (compilation, environment, patches)
    # and create the pyconf file to add to the project
    lproducts_name = config.APPLICATION.products.keys()
    l_products = src.product.get_products_infos(lproducts_name, config)
    for p_name, p_info in l_products:
        find_product_scripts_and_pyconf(p_name,
                                        p_info,
                                        config,
                                        with_vcs,
                                        compil_scripts_tmp_dir,
                                        env_scripts_tmp_dir,
                                        patches_tmp_dir,
                                        products_pyconf_tmp_dir)
    
    find_application_pyconf(config, application_tmp_dir)
    
    d_project = {"project" : (project_tmp_dir, PROJECT_DIR )}
    return d_project

def find_product_scripts_and_pyconf(p_name,
                                    p_info,
                                    config,
                                    with_vcs,
                                    compil_scripts_tmp_dir,
                                    env_scripts_tmp_dir,
                                    patches_tmp_dir,
                                    products_pyconf_tmp_dir):
    '''Create a specific pyconf file for a given product. Get its environment 
       script, its compilation script and patches and put it in the temporary
       working directory. This method is used in the source package in order to
       construct the specific project.

    :param p_name str: The name of the product.
    :param p_info Config: The specific configuration corresponding to the 
                             product
    :param config Config: The global configuration.
    :param with_vcs boolean: True if the package is with vcs products (not 
                             transformed into archive products)
    :param compil_scripts_tmp_dir str: The path to the temporary compilation 
                                       scripts directory of the project.
    :param env_scripts_tmp_dir str: The path to the temporary environment script 
                                    directory of the project.
    :param patches_tmp_dir str: The path to the temporary patch scripts 
                                directory of the project.
    :param products_pyconf_tmp_dir str: The path to the temporary product 
                                        scripts directory of the project.
    '''
    
    # read the pyconf of the product
    product_pyconf_path = UTS.find_file_in_lpath(p_name + ".pyconf",
                                           config.PATHS.PRODUCTPATH)
    product_pyconf_cfg = PYCONF.Config(product_pyconf_path)

    # find the compilation script if any
    if src.product.product_has_script(p_info):
        compil_script_path = src.Path(p_info.compil_script)
        compil_script_path.copy(compil_scripts_tmp_dir)
        product_pyconf_cfg[p_info.section].compil_script = os.path.basename(
                                                    p_info.compil_script)
    # find the environment script if any
    if src.product.product_has_env_script(p_info):
        env_script_path = src.Path(p_info.environ.env_script)
        env_script_path.copy(env_scripts_tmp_dir)
        product_pyconf_cfg[p_info.section].environ.env_script = os.path.basename(
                                                p_info.environ.env_script)
    # find the patches if any
    if src.product.product_has_patches(p_info):
        patches = PYCONF.Sequence()
        for patch_path in p_info.patches:
            p_path = src.Path(patch_path)
            p_path.copy(patches_tmp_dir)
            patches.append(os.path.basename(patch_path), "")

        product_pyconf_cfg[p_info.section].patches = patches
    
    if with_vcs:
        # put in the pyconf file the resolved values
        for info in ["git_info", "cvs_info", "svn_info"]:
            if info in p_info:
                for key in p_info[info]:
                    product_pyconf_cfg[p_info.section][info][key] = p_info[
                                                                      info][key]
    else:
        # if the product is not archive, then make it become archive.
        if src.product.product_is_vcs(p_info):
            product_pyconf_cfg[p_info.section].get_source = "archive"
            if not "archive_info" in product_pyconf_cfg[p_info.section]:
                product_pyconf_cfg[p_info.section].addMapping("archive_info",
                                        PYCONF.Mapping(product_pyconf_cfg),
                                        "")
            product_pyconf_cfg[p_info.section
                              ].archive_info.archive_name = p_info.name + ".tgz"
    
    # write the pyconf file to the temporary project location
    product_tmp_pyconf_path = os.path.join(products_pyconf_tmp_dir,
                                           p_name + ".pyconf")
    ff = open(product_tmp_pyconf_path, 'w')
    ff.write("#!/usr/bin/env python\n#-*- coding:utf-8 -*-\n\n")
    product_pyconf_cfg.__save__(ff, 1)
    ff.close()

def find_application_pyconf(config, application_tmp_dir):
    '''Find the application pyconf file and put it in the specific temporary 
       directory containing the specific project of a source package.

    :param config Config: The global configuration.
    :param application_tmp_dir str: The path to the temporary application 
                                       scripts directory of the project.
    '''
    # read the pyconf of the application
    application_name = config.VARS.application
    application_pyconf_path = UTS.find_file_in_lpath(
                                            application_name + ".pyconf",
                                            config.PATHS.APPLICATIONPATH)
    application_pyconf_cfg = PYCONF.Config(application_pyconf_path)
    
    # Change the workdir
    application_pyconf_cfg.APPLICATION.workdir = PYCONF.Reference(
                                    application_pyconf_cfg,
                                    PYCONF.DOLLAR,
                                    'VARS.salometoolsway + $VARS.sep + ".."')

    # Prevent from compilation in base
    application_pyconf_cfg.APPLICATION.no_base = "yes"
    
    # write the pyconf file to the temporary application location
    application_tmp_pyconf_path = os.path.join(application_tmp_dir,
                                               application_name + ".pyconf")
    ff = open(application_tmp_pyconf_path, 'w')
    ff.write("#!/usr/bin/env python\n#-*- coding:utf-8 -*-\n\n")
    application_pyconf_cfg.__save__(ff, 1)
    ff.close()

def project_package(project_file_path, tmp_working_dir):
    '''Prepare a dictionary that stores all the needed directories and files to
       add in a project package.
    
    :param project_file_path str: The path to the local project.
    :param tmp_working_dir str: The temporary local directory containing some 
                                specific directories or files needed in the 
                                project package
    :return: the dictionary that stores all the needed directories and files to
             add in a project package.
             {label : (path_on_local_machine, path_in_archive)}
    :rtype: dict
    '''
    d_project = {}
    # Read the project file and get the directories to add to the package
    project_pyconf_cfg = PYCONF.Config(project_file_path)
    paths = {"ARCHIVEPATH" : "archives",
             "APPLICATIONPATH" : "applications",
             "PRODUCTPATH" : "products",
             "JOBPATH" : "jobs",
             "MACHINEPATH" : "machines"}
    # Loop over the project paths and add it
    for path in paths:
        if path not in project_pyconf_cfg:
            continue
        # Add the directory to the files to add in the package
        d_project[path] = (project_pyconf_cfg[path], paths[path])
        # Modify the value of the path in the package
        project_pyconf_cfg[path] = PYCONF.Reference(
                                    project_pyconf_cfg,
                                    PYCONF.DOLLAR,
                                    'project_path + "/' + paths[path] + '"')
    
    # Modify some values
    if "project_path" not in project_pyconf_cfg:
        project_pyconf_cfg.addMapping("project_path",
                                      PYCONF.Mapping(project_pyconf_cfg),
                                      "")
    project_pyconf_cfg.project_path = PYCONF.Reference(project_pyconf_cfg,
                                                           PYCONF.DOLLAR,
                                                           'PWD')
    
    # Write the project pyconf file
    project_file_name = os.path.basename(project_file_path)
    project_pyconf_tmp_path = os.path.join(tmp_working_dir, project_file_name)
    ff = open(project_pyconf_tmp_path, 'w')
    ff.write("#!/usr/bin/env python\n#-*- coding:utf-8 -*-\n\n")
    project_pyconf_cfg.__save__(ff, 1)
    ff.close()
    d_project["Project hat file"] = (project_pyconf_tmp_path, project_file_name)
    
    return d_project

def add_readme(config, options, where):
    readme_path = os.path.join(where, "README")
    with codecs.open(readme_path, "w", 'utf-8') as f:

    # templates for building the header
        readme_header="""
# This package was generated with sat $version
# Date: $date
# User: $user
# Distribution : $dist

In the following, $$ROOT represents the directory where you have installed 
SALOME (the directory where this file is located).

"""
        readme_compilation_with_binaries="""

compilation based on the binaries used as prerequisites
=======================================================

If you fail to compile the complete application (for example because
you are not root on your system and cannot install missing packages), you
may try a partial compilation based on the binaries.
For that it is necessary to copy the binaries from BINARIES to INSTALL,
and do some substitutions on cmake and .la files (replace the build directories
with local paths).
The procedure to do it is:
  1) Remove or rename INSTALL directory if it exists
  2) Execute the shell script install_bin.sh:
     >> cd $ROOT
     >> ./install_bin.sh
  3) Use SalomeTool (as explained in Sources section) and compile only the 
     modules you need to (with -p option)

"""
        readme_header_tpl=string.Template(readme_header)
        readme_template_path_bin = os.path.join(config.VARS.internal_dir,
                "README_BIN.template")
        readme_template_path_bin_launcher = os.path.join(config.VARS.internal_dir,
                "README_LAUNCHER.template")
        readme_template_path_bin_virtapp = os.path.join(config.VARS.internal_dir,
                "README_BIN_VIRTUAL_APP.template")
        readme_template_path_src = os.path.join(config.VARS.internal_dir,
                "README_SRC.template")
        readme_template_path_pro = os.path.join(config.VARS.internal_dir,
                "README_PROJECT.template")
        readme_template_path_sat = os.path.join(config.VARS.internal_dir,
                "README_SAT.template")

        # prepare substitution dictionary
        d = dict()
        d['user'] = config.VARS.user
        d['date'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        d['version'] = config.INTERNAL.sat_version
        d['dist'] = config.VARS.dist
        f.write(readme_header_tpl.substitute(d)) # write the general header (common)

        if options.binaries or options.sources:
            d['application'] = config.VARS.application
            f.write("# Application: " + d['application'] + "\n")
            if 'KERNEL' in config.APPLICATION.products:
                VersionSalome = src.get_salome_version(config)
                # Case where SALOME has the launcher that uses the SalomeContext API
                if VersionSalome >= 730:
                    d['launcher'] = config.APPLICATION.profile.launcher_name
                else:
                    d['virtual_app'] = 'runAppli' # this info is not used now)

        # write the specific sections
        if options.binaries:
            f.write(src.template.substitute(readme_template_path_bin, d))
            if "virtual_app" in d:
                f.write(src.template.substitute(readme_template_path_bin_virtapp, d))
            if "launcher" in d:
                f.write(src.template.substitute(readme_template_path_bin_launcher, d))

        if options.sources:
            f.write(src.template.substitute(readme_template_path_src, d))

        if options.binaries and options.sources:
            f.write(readme_compilation_with_binaries)

        if options.project:
            f.write(src.template.substitute(readme_template_path_pro, d))

        if options.sat:
            f.write(src.template.substitute(readme_template_path_sat, d))
    
    return readme_path

def update_config(config, prop, value):
    '''Remove from config.APPLICATION.products the products that have the property given as input.
    
    :param config Config: The global config.
    :param prop str: The property to filter
    :param value str: The value of the property to filter
    '''
    src.check_config_has_application(config)
    l_product_to_remove = []
    for product_name in config.APPLICATION.products.keys():
        prod_cfg = src.product.get_product_config(config, product_name)
        if src.get_property_in_product_cfg(prod_cfg, prop) == value:
            l_product_to_remove.append(product_name)
    for product_name in l_product_to_remove:
        config.APPLICATION.products.__delitem__(product_name)
