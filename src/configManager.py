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
import platform
import datetime
import shutil
import sys

import src.debug as DBG
import src.loggingSat as LOG
import src.returnCode as RCO
import src.architecture as ARCH
import src.utilsSat as UTS
import src.pyconf as PYCONF

class ConfigOpener:
    """
    Class that helps to find an application pyconf 
    in all the possible directories (pathList)
    """
    def __init__(self, pathList):
        """Initialization
        
        :param pathList: (list) 
          The list of paths where to search a pyconf.
        """
        self.pathList = pathList

    def __call__(self, name):
        if os.path.isabs(name):
            return PYCONF.ConfigInputStream(open(name, 'rb'))
        else:
            return PYCONF.ConfigInputStream( 
                        open(os.path.join( self.get_path(name), name ), 'rb') )
        raise IOError(_("Configuration file '%s' not found") % name)

    def get_path( self, name):
        """The method that returns the entire path of the pyconf searched
        
        :param name: (str) The name of the searched pyconf.
        """
        for path in self.pathList:
            if os.path.exists(os.path.join(path, name)):
                return path
        raise IOError(_("Configuration file '%s' not found") % name)

class ConfigManager:
    """
    Class that manages the read of all the config .pyconf files of salomeTools
    """
    def __init__(self, runner):
        self.runner = runner
        self.logger = runner.getLogger()
        self.datadir = None

    def _create_vars(self, application=None, command=None, datadir=None):
        """
        Create a dictionary that stores all information about machine,
        user, date, repositories, etc...
        
        :param application: (str) 
          The application for which salomeTools is called.
        :param command: (str) The command that is called.
        :param datadir: (str) 
          The repository that contain external data for salomeTools.
        :return: (dict) The dictionary that stores all information.
        """
        var = {}      
        var['user'] = ARCH.get_user()
        var['salometoolsway'] = os.path.dirname(
                                    os.path.dirname(os.path.abspath(__file__)))
        var['srcDir'] = os.path.join(var['salometoolsway'], 'src')
        var['internal_dir'] = os.path.join(var['srcDir'], 'internal_config')
        var['sep']= os.path.sep
        
        # datadir has a default location
        var['datadir'] = os.path.join(var['salometoolsway'], 'data')
        if datadir is not None:
            var['datadir'] = datadir

        var['personalDir'] = os.path.join(os.path.expanduser('~'),
                                           '.salomeTools')
        UTS.ensure_path_exists(var['personalDir'])

        var['personal_applications_dir'] = os.path.join(var['personalDir'],
                                                        "Applications")
        UTS.ensure_path_exists(var['personal_applications_dir'])
        
        var['personal_products_dir'] = os.path.join(var['personalDir'],
                                                    "products")
        UTS.ensure_path_exists(var['personal_products_dir'])
        
        var['personal_archives_dir'] = os.path.join(var['personalDir'],
                                                    "Archives")
        UTS.ensure_path_exists(var['personal_archives_dir'])

        var['personal_jobs_dir'] = os.path.join(var['personalDir'],
                                                "Jobs")
        UTS.ensure_path_exists(var['personal_jobs_dir'])

        var['personal_machines_dir'] = os.path.join(var['personalDir'],
                                                    "Machines")
        UTS.ensure_path_exists(var['personal_machines_dir'])

        # read linux distributions dictionary
        distrib_cfg = PYCONF.Config(os.path.join(var['srcDir'],
                                                      'internal_config',
                                                      'distrib.pyconf'))
        
        # set platform parameters
        dist_name = ARCH.get_distribution(codes=distrib_cfg.DISTRIBUTIONS)
        dist_version = ARCH.get_distrib_version(dist_name, 
                                                codes=distrib_cfg.VERSIONS)
        dist = dist_name + dist_version
        
        var['dist_name'] = dist_name
        var['dist_version'] = dist_version
        var['dist'] = dist
        var['python'] = ARCH.get_python_version()

        var['nb_proc'] = ARCH.get_nb_proc()
        node_name = platform.node()
        var['node'] = node_name
        var['hostname'] = node_name

        # set date parameters
        dt = datetime.datetime.now()
        var['date'] = dt.strftime('%Y%m%d')
        var['datehour'] = dt.strftime('%Y%m%d_%H%M%S')
        var['hour'] = dt.strftime('%H%M%S')

        var['command'] = str(command)
        var['application'] = str(application)

        # Root dir for temporary files 
        var['tmp_root'] = os.sep + 'tmp' + os.sep + var['user']
        # particular win case 
        if ARCH.is_windows() : 
            var['tmp_root'] =  os.path.expanduser('~') + os.sep + 'tmp'
        
        return var

    def get_command_line_overrides(self, options, sections):
        """get all the overwrites that are in the command line
        
        :param options:
          The options from salomeTools class initialization 
          (as '-l5' or '--overwrite')
        :param sections: (str) The config section to overwrite.
        :return: (list) The list of all the overwrites to apply.
        """
        # when there are no options or not the overwrite option, 
        # return an empty list
        if options is None or options.overwrite is None:
            return []
        
        over = []
        for section in sections:
            # only overwrite the sections that correspond to the option 
            over.extend(filter(lambda l: l.startswith(section + "."), 
                               options.overwrite))
        return over

    def get_config(self, application=None, options=None, command=None,
                    datadir=None):
        """get the config from all the configuration files.
        
        :param application: (str) 
          The application for which salomeTools is called.
        :param options: (Options) 
          The general salomeTools options 
          (as '--overwrite' or '-v5')
        :param command: (str) The command that is called.
        :param datadir: (str) 
          The repository that contain external data for salomeTools.
        :return: (Config) The final config.
        """        
        msgPb = _("Problem in configuration file: <red>%s\n<yellow>%s<reset>\n") # % (filename, exception)
        # create a ConfigMerger to handle merge
        merger = PYCONF.ConfigMerger() #MergeHandler())
        
        # create the configuration instance
        cfg = PYCONF.Config()
        
        # =====================================================================
        # create VARS section
        var = self._create_vars(application=application, command=command, 
                                datadir=datadir)
        # add VARS to config
        cfg.VARS = PYCONF.Mapping(cfg)
        for variable in var:
            cfg.VARS[variable] = var[variable]
        
        # apply overwrite from command line if needed
        for rule in self.get_command_line_overrides(options, ["VARS"]):
            exec('cfg.' + rule) # this cannot be factorized because of the exec
        
        # =====================================================================
        # Load INTERNAL config
        # read src/internal_config/salomeTools.pyconf
        intDir = os.path.join(cfg.VARS.srcDir, 'internal_config')
        PYCONF.streamOpener = ConfigOpener([intDir])
        try:
          afile = os.path.join(intDir, 'salomeTools.pyconf')
          with open(afile) as f:
           internal_cfg = PYCONF.Config(f)
        except Exception as e:
          raise Exception(msgPb % (afile, str(e)))
        
        merger.merge(cfg, internal_cfg)

        # apply overwrite from command line if needed
        for rule in self.get_command_line_overrides(options, ["INTERNAL"]):
            exec('cfg.' + rule) # this cannot be factorized because of the exec        
               
        # =====================================================================
        # Load LOCAL config file
        # search only in the data directory
        PYCONF.streamOpener = ConfigOpener([cfg.VARS.datadir])
        try:
          aFile = os.path.join(cfg.VARS.datadir, 'local.pyconf')
          with open(aFile) as f:
            local_cfg = PYCONF.Config(f, PWD = ('LOCAL', cfg.VARS.datadir) )
        except Exception as e:
          raise Exception(msgPb % (aFile, str(e)))
        
        merger.merge(cfg, local_cfg)

        # When the key is "default", put the default value
        sWay = cfg.VARS.salometoolsway
        if cfg.LOCAL.base == "default":
            cfg.LOCAL.base = os.path.abspath(os.path.join(sWay, "..", "BASE"))
        if cfg.LOCAL.workdir == "default":
            cfg.LOCAL.workdir = os.path.abspath(os.path.join(sWay, ".."))
        if cfg.LOCAL.log_dir == "default":
            cfg.LOCAL.log_dir = os.path.abspath(os.path.join(sWay, "..", "LOGS"))
        if cfg.LOCAL.archive_dir == "default":
            cfg.LOCAL.archive_dir = os.path.abspath(os.path.join(sWay, "..", "ARCHIVES"))

        # apply overwrite from command line if needed
        for rule in self.get_command_line_overrides(options, ["LOCAL"]):
            exec('cfg.' + rule) # this cannot be factorized because of the exec
        
        # =====================================================================
        # Load the PROJECTS
        projects_cfg = PYCONF.Config()
        projects_cfg.addMapping("PROJECTS", PYCONF.Mapping(projects_cfg), "The projects\n")
        projects_cfg.PROJECTS.addMapping("projects", PYCONF.Mapping(cfg.PROJECTS), "The projects definition\n")
        
        for project_pyconf_path in cfg.PROJECTS.project_file_paths:
            if not os.path.exists(project_pyconf_path):
                msg = _("Cannot find project file %s, Ignored.") % UTS.red(project_pyconf_path)
                self.logger.warning(msg)
                continue
            project_name = os.path.basename(project_pyconf_path)[:-len(".pyconf")]
            try:
              project_pyconf_dir = os.path.dirname(project_pyconf_path)
              with open(project_pyconf_path) as f:
                project_cfg = PYCONF.Config(f, PWD=("", project_pyconf_dir))
            except Exception as e:
              self.logger.warning(msgPb % (project_pyconf_path, str(e)))
              continue
            PROJECTS = projects_cfg.PROJECTS
            PROJECTS.projects.addMapping(project_name, 
                                         PYCONF.Mapping(PROJECTS.projects),
                                         "The %s project\n" % project_name)
            PROJECTS.projects[project_name] = project_cfg
            PROJECTS.projects[project_name]["file_path"] = project_pyconf_path
                   
        merger.merge(cfg, projects_cfg)

        # apply overwrite from command line if needed
        for rule in self.get_command_line_overrides(options, ["PROJECTS"]):
            exec('cfg.' + rule) # this cannot be factorized because of the exec
        
        # =====================================================================
        # Create the paths where to search the application configurations, 
        # the product configurations, the products archives, 
        # the jobs configurations and the machines configurations
        cfg.addMapping("PATHS", PYCONF.Mapping(cfg), "The paths\n")
        cfg.PATHS["APPLICATIONPATH"] = PYCONF.Sequence(cfg.PATHS)
        cfg.PATHS.APPLICATIONPATH.append(cfg.VARS.personal_applications_dir, "")
        
        cfg.PATHS["PRODUCTPATH"] = PYCONF.Sequence(cfg.PATHS)
        cfg.PATHS.PRODUCTPATH.append(cfg.VARS.personal_products_dir, "")
        cfg.PATHS["ARCHIVEPATH"] = PYCONF.Sequence(cfg.PATHS)
        cfg.PATHS.ARCHIVEPATH.append(cfg.VARS.personal_archives_dir, "")
        cfg.PATHS["JOBPATH"] = PYCONF.Sequence(cfg.PATHS)
        cfg.PATHS.JOBPATH.append(cfg.VARS.personal_jobs_dir, "")
        cfg.PATHS["MACHINEPATH"] = PYCONF.Sequence(cfg.PATHS)
        cfg.PATHS.MACHINEPATH.append(cfg.VARS.personal_machines_dir, "")

        # initialise the path with local directory
        cfg.PATHS["ARCHIVEPATH"].append(cfg.LOCAL.archive_dir, "")

        # Loop over the projects in order to complete the PATHS variables
        for project in cfg.PROJECTS.projects:
            for PATH in ["APPLICATIONPATH",
                         "PRODUCTPATH",
                         "ARCHIVEPATH",
                         "JOBPATH",
                         "MACHINEPATH"]:
                if PATH not in cfg.PROJECTS.projects[project]:
                    continue
                cfg.PATHS[PATH].append(cfg.PROJECTS.projects[project][PATH], "")
        
        # apply overwrite from command line if needed
        for rule in self.get_command_line_overrides(options, ["PATHS"]):
            exec('cfg.' + rule) # this cannot be factorized because of the exec

        # =====================================================================
        # Load APPLICATION config file
        if application is not None:
            # search APPLICATION file in all directories in configPath
            cp = cfg.PATHS.APPLICATIONPATH
            PYCONF.streamOpener = ConfigOpener(cp)
            do_merge = True
            aFile = application + '.pyconf'
            try:
              application_cfg = PYCONF.Config(aFile)
            except IOError as e:
              msg = msgPb % (aFile, str(e))
              msg += "\n" + _("(use 'sat config --list' to get the list of available applications)")
              raise Exception(msg)
            except PYCONF.ConfigError as e:
              msg = msgPb % (aFile, str(e))
              if (not ('-e' in parser.parse_args()[1]) 
                  or ('--edit' in parser.parse_args()[1]) 
                  and command == 'config'):
                  raise Exception(msg)
              else:
                  self.warning(msg)
                  do_merge = False
            except Exception as e:
              msg = msgPb % (aFile, str(e))
              if (not('-e' in parser.parse_args()[1])
                  or ('--edit' in parser.parse_args()[1])
                  and command == 'config' ):
                  self.warning(msg)
                  raise Exception(msg)
              else:
                  self.warning("Opening the file %s with the default viewer" % aFile)
                  do_merge = False
        
            else:
                cfg['open_application'] = 'yes'

        # =====================================================================
        # Load product config files in PRODUCTS section
        products_cfg = PYCONF.Config()
        products_cfg.addMapping("PRODUCTS", PYCONF.Mapping(products_cfg), "The products\n")
        if application is not None:
            PYCONF.streamOpener = ConfigOpener(cfg.PATHS.PRODUCTPATH)
            for product_name in application_cfg.APPLICATION.products.keys():
                # Loop on all files that are in softsDir directory
                # and read their config
                product_file_name = product_name + ".pyconf"
                product_file_path = UTS.find_file_in_lpath(product_file_name, cfg.PATHS.PRODUCTPATH)
                if product_file_path:
                    products_dir = os.path.dirname(product_file_path)
                    try:
                        prod_cfg = PYCONF.Config(open(product_file_path), PWD=("", products_dir))
                        prod_cfg.from_file = product_file_path
                        products_cfg.PRODUCTS[product_name] = prod_cfg
                    except Exception as e:
                        msg = msgPb % (product_name, str(e))
                        self.logger.warning(msg)
            
            merger.merge(cfg, products_cfg)
            
            # apply overwrite from command line if needed
            for rule in self.get_command_line_overrides(options, ["PRODUCTS"]):
                exec('cfg.' + rule) # this cannot be factorized because of the exec
            
            if do_merge:
                merger.merge(cfg, application_cfg)

                # default launcher name ('salome')
                if ('profile' in cfg.APPLICATION and 
                    'launcher_name' not in cfg.APPLICATION.profile):
                    cfg.APPLICATION.profile.launcher_name = 'salome'

                # apply overwrite from command line if needed
                for rule in self.get_command_line_overrides(options,
                                                             ["APPLICATION"]):
                    # this cannot be factorized because of the exec
                    exec('cfg.' + rule)
            
        # =====================================================================
        # load USER config
        self.set_user_config_file(cfg)
        user_cfg_file = self.get_user_config_file()
        user_cfg = PYCONF.Config(open(user_cfg_file))
        merger.merge(cfg, user_cfg)

        # apply overwrite from command line if needed
        for rule in self.get_command_line_overrides(options, ["USER"]):
            exec('cfg.' + rule) # this cannot be factorize because of the exec
        
        return cfg

    def set_user_config_file(self, config):
        """
        Set the user config file name and path.
        If necessary, build it from another one or create it from scratch.
        
        :param config: (Config) 
          The global config (containing all pyconf).
        """
        # get the expected name and path of the file
        self.config_file_name = 'SAT.pyconf'
        self.user_config_file_path = os.path.join(config.VARS.personalDir,
                                                   self.config_file_name)
        
        # if pyconf does not exist, create it from scratch
        if not os.path.isfile(self.user_config_file_path): 
            self.create_config_file(config)
    
    def create_config_file(self, config):
        """
        This method is called when there are no user config file. 
        It build it from scratch.
        
        :param config: (Config) The global config.
        :return: (Config) 
          The config corresponding to the file created.
        """
        
        cfg_name = self.get_user_config_file()
        cfg = PYCONF.Config()
        cfg.addMapping('USER', PYCONF.Mapping(user_cfg), "")
        USER = cfg.USER

        USER.addMapping('cvs_user', config.VARS.user, 
                        "This is the user name used to access salome cvs base.\n")
        USER.addMapping('svn_user', config.VARS.user, 
                        "This is the user name used to access salome svn base.\n")
        USER.addMapping('output_verbose_level', 3,
                        "This is the default output_verbose_level you want. 0=>no output, 5=>debug.\n")
        USER.addMapping('publish_dir', os.path.join(os.path.expanduser('~'), 'websupport', 'satreport'), 
                        "")
        USER.addMapping('editor', 'vi', "This is the editor used to modify configuration files\n")
        USER.addMapping('browser', 'firefox', "This is the browser used to read html documentation\n")
        USER.addMapping('pdf_viewer', 'evince', "This is the pdf_viewer used to read pdf documentation\n")
               
        UTS.ensure_path_exists(config.VARS.personalDir)
        UTS.ensure_path_exists(os.path.join(config.VARS.personalDir, 'Applications'))

        with open(cfg_name, 'w') as f:
          cfg.__save__(f)
        return cfg   

    def get_user_config_file(self):
        """Get the user config file
        
        :return: (str) path to the user config file.
        """
        if not self.user_config_file_path:
            raise Exception(_("get_user_config_file: missing user config file path"))
        return self.user_config_file_path     

def check_path(path, ext=[]):
    """Construct a text with the input path and "not found" if it does not exist.
    
    :param path: (str) The path to check.
    :param ext: (list) 
      An extension. Verify that the path extension is in the list
    :return: (str) The string of the path with information
    """
    # check if file exists
    if not os.path.exists(path):
        return "path '%s' ** not found" % path

    # check extension
    if len(ext) > 0:
        fe = os.path.splitext(path)[1].lower()
        if fe not in ext:
            return "path '%s' ** bad extension" % path

    return path

def show_product_info(config, name, logger):
    """Display on the terminal and logger information about a product.
    
    :param config: (Config) the global configuration.
    :param name: (str) The name of the product
    :param logger: (Logger) The logger instance to use for the display
    """
    
    def msgAdd(label, value):
        """
        local short named macro for convenience
        appending show_product_info.msg variable
        """
        msg += "  %s = %s\n" % (label, value)
        return
    
    msg = "" # used msgAdd()
    msg += _("%s is a product\n") % UTS.blue(name)
    pinfo = src.product.get_product_config(config, name)

    if "depend" in pinfo:
        msgAdd("depends on", ', '.join(pinfo.depend))

    if "opt_depend" in pinfo:
        msgAdd("optional", ', '.join(pinfo.opt_depend))

    # information on pyconf
    msg += UTS.label("configuration:\n")
    if "from_file" in pinfo:
        msgAdd("pyconf file path", pinfo.from_file)
    if "section" in pinfo:
        msgAdd("section", pinfo.section)

    # information on prepare
    msg += UTS.label("prepare:\n")

    is_dev = src.product.product_is_dev(pinfo)
    method = pinfo.get_source
    if is_dev:
        method += " (dev)"
    msgAdd("get method", method)

    if method == 'cvs':
        msgAdd("server", pinfo.cvs_info.server)
        msgAdd("base module", pinfo.cvs_info.module_base)
        msgAdd("source", pinfo.cvs_info.source)
        msgAdd("tag", pinfo.cvs_info.tag)

    elif method == 'svn':
        msgAdd("repo", pinfo.svn_info.repo)

    elif method == 'git':
        msgAdd("repo", pinfo.git_info.repo)
        msgAdd("tag", pinfo.git_info.tag)

    elif method == 'archive':
        msgAdd("get from", check_path(pinfo.archive_info.archive_name))

    if 'patches' in pinfo:
        for patch in pinfo.patches:
            msgAdd("patch", check_path(patch))

    if src.product.product_is_fixed(pinfo):
        msgAdd("install_dir", check_path(pinfo.install_dir))

    logger.info(msg) # return possible
    if src.product.product_is_native(pinfo) or src.product.product_is_fixed(pinfo):
        return
    
    # information on compilation
    msg = "\n\n"
    if src.product.product_compiles(pinfo):
        msg += "compile:\n"
        msgAdd("compilation method", pinfo.build_source)
        if pinfo.build_source == "script" and "compil_script" in pinfo:
            msgAdd("Compilation script", pinfo.compil_script)
        if 'nb_proc' in pinfo:
            msgAdd("make -j", pinfo.nb_proc)
        msgAdd("source dir", check_path(pinfo.source_dir))
        if 'install_dir' in pinfo:
            msgAdd("build dir", check_path(pinfo.build_dir))
            msgAdd("install dir", check_path(pinfo.install_dir))
        else:
            msg += "  %s\n" % UTS.red(_("no install dir"))
    else:
        msg += "%s\n" % UTS.red(_("This product does not compile"))

    logger.info(msg)
    
    # information on environment
    msg = UTS.label("\nenviron:\n")
    if "environ" in pinfo and "env_script" in pinfo.environ:
        msgAdd("script", check_path(pinfo.environ.env_script))
    logger.info(msg)
    
    zz = src.environment.SalomeEnviron(
           config, src.fileEnviron.ScreenEnviron(logger), False)
    zz.set_python_libdirs()
    
    zz.set_a_product(name, logger)
    return
        
def show_patchs(config, logger):
    """Prints all the used patchs in the application.
    
    :param config: (Config) the global configuration.
    :param logger: (Logger) 
      The logger instance to use for the display
    """
    len_max = max([len(p) for p in config.APPLICATION.products]) + 2
    msg = ""
    for product in config.APPLICATION.products:
        nb = len_max-len(product)-2
        product_info = src.product.get_product_config(config, product)
        if src.product.product_has_patches(product_info):
            msg += "<header>%s: <reset>" % product
            msg += " "*nb + "%s\n" % product_info.patches[0]
            if len(product_info.patches) > 1:
                for patch in product_info.patches[1:]:
                    msg += " "*nb + "%s\n" % patch
            msg += "\n"
    logger.info(msg)
    return

def getConfigColored(config, path, stream, show_label=False, level=0, show_full_path=False):
    """
    Get a colored representation value from a config pyconf instance.
    used recursively from the initial path.
    
    :param config: (Config) 
      The configuration from which the value is displayed.
    :param path: (str) The path in the configuration of the value to print.
    :param show_label: (bool) 
      If True, do a basic display. (useful for bash completion)
    :param stream: The output stream used
    :param level: (int) The number of spaces to add before display.
    :param show_full_path: (bool) Display full path, else relative
    """           
    
    # Make sure that the path does not ends with a point
    if path.endswith('.'):
        path = path[:-1]
    
    # display all the path or not
    if show_full_path:
        vname = path
    else:
        vname = path.split('.')[-1]

    # number of spaces before the display
    tab_level = "  " * level
    
    # call to the function that gets the value of the path.
    try:
        val = config.getByPath(path)
    except Exception as e:
        stream.write(tab_level + "<header>%s: <red>ERROR %s<reset>\n" % (vname, str(e)))
        return

    # in this case, display only the value
    if show_label:
        stream.write(tab_level + "<header>%s: <reset>" % vname)

    # The case where the value has under values, 
    # do a recursive call to the function
    if dir(val).__contains__('keys'):
        if show_label: stream.write("\n")
        for v in sorted(val.keys()):
            getConfigColored(config, path + '.' + v, stream, show_label, level + 1)
    elif val.__class__ == PYCONF.Sequence or isinstance(val, list): 
        # in this case, value is a list (or a Sequence)
        if show_label: stream.write("\n")
        index = 0
        for v in val:
            p = path + "[" + str(index) + "]"
            getConfigColored(config, p, stream, show_label, level + 1)
            index += 1
    else: # case where val is just a str
        stream.write("%s\n" % val)
        
def print_value(config, path, logger, show_label=False, level=0, show_full_path=False):
    """
    print a colored representation value from a config pyconf instance.
    used recursively from the initial path.
    
    :param: as getConfigColored
    """ 
    outStream = DBG.OutStream()
    getConfigColored(config, path, outStream, show_label, level, show_full_path)
    res = outStream.getvalue() # stream not closed
    logger.info(res)
    return

     
def print_debug(config, aPath, logger, show_label=False, level=0, show_full_path=False):
    """
    logger output for debugging a config/pyconf
    lines contains: path : expression --> 'evaluation'
    
    example:
    PROJECTS.projects.salome.project_path : $PWD --> '/tmp/SALOME'
    """
    path = str(aPath)
    if path == "." :
      val = config
      path = ""
    else:
      if path.endswith('.'): # Make sure that the path does not ends with a point
        path = path[:-1]
      val = config.getByPath(path)
      
    outStream = DBG.OutStream()
    DBG.saveConfigDbg(val, outStream, path=path)
    res = outStream.value
    logger.info(res)
    return


def get_config_children(config, args):
    """
    Gets the names of the children of the given parameter.
    Useful only for completion mechanism
    
    :param config: (Config) The configuration where to read the values
    :param args: The path in the config from which get the keys
    """
    vals = []
    rootkeys = config.keys()
    
    if len(args) == 0:
        # no parameter returns list of root keys
        vals = rootkeys
    else:
        parent = args[0]
        pos = parent.rfind('.')
        if pos < 0:
            # Case where there is only on key as parameter.
            # For example VARS
            vals = [m for m in rootkeys if m.startswith(parent)]
        else:
            # Case where there is a part from a key
            # for example VARS.us  (for VARS.user)
            head = parent[0:pos]
            tail = parent[pos+1:]
            try:
                a = config.getByPath(head)
                if dir(a).__contains__('keys'):
                    vals = map(lambda x: head + '.' + x,
                               [m for m in a.keys() if m.startswith(tail)])
            except:
                pass

    for v in sorted(vals):
        sys.stdout.write("%s\n" % v)


def _getConfig(self, appliToLoad):
        """
        Load the configuration (all pyconf)
        and returns the config from some files .pyconf
        """
        if self.runner.config is not None:
          raise Exception("config existing yet in '%s' instance" % self.runner.getClassName())
          

        # read the configuration from all the pyconf files    
        cfgManager = getConfigManager() # commands.config.ConfigManager()
        DBG.write("appli to load", appliToLoad, True)
        config = cfgManager.get_config(datadir=self.runner.datadir, 
                                       application=appliToLoad, 
                                       options=self.runner.options, 
                                       command=self.name)
        self.runner.nameAppliLoaded = appliToLoad
        # DBG.write("appli loaded", config, True)
                       
        # Set the verbose mode if called
        DBG.tofix("verbose/batch/logger_add_link -1/False/None", True)
        verbose = -1
        batch = False
        logger_add_link = None
        if verbose > -1:
            verbose_save = self.options.output_verbose_level
            self.options.__setattr__("output_verbose_level", verbose)    

        # Set batch mode if called
        if batch:
            batch_save = self.options.batch
            self.options.__setattr__("batch", True)

        # set output level
        if self.runner.options.output_verbose_level is not None:
            config.USER.output_verbose_level = self.runner.options.output_verbose_level
        if config.USER.output_verbose_level < 1:
            config.USER.output_verbose_level = 0
        silent = (config.USER.output_verbose_level == 0)

        # create log file
        micro_command = False
        if logger_add_link:
            micro_command = True
        logger_command = UTS.getNewLogger(config, 
                           silent_sysstd=silent,
                           all_in_terminal=self.runner.options.all_in_terminal,
                           micro_command=micro_command)
        
        # Check that the path given by the logs_paths_in_file option
        # is a file path that can be written
        if self.runner.options.logs_paths_in_file and not micro_command:
            try:
                self.options.logs_paths_in_file = os.path.abspath(
                                        self.options.logs_paths_in_file)
                dir_file = os.path.dirname(self.options.logs_paths_in_file)
                if not os.path.exists(dir_file):
                    os.makedirs(dir_file)
                if os.path.exists(self.options.logs_paths_in_file):
                    os.remove(self.options.logs_paths_in_file)
                file_test = open(self.options.logs_paths_in_file, "w")
                file_test.close()
            except Exception as e:
                msg = _("""\
The logs_paths_in_file option will not be taken into account.
Here is the error:""")
                logger_command.warning("%s\n%s" % (msg, str(e)))
                self.options.logs_paths_in_file = None
                
        return config

def get_products_list(self, options, cfg, logger):
        """
        Gives the product list with their informations from 
        configuration regarding the passed options.
        
        :param options: (Options) 
          The Options instance that stores the commands arguments
        :param config: (Config) The global configuration
        :param logger: (Logger) 
          The logger instance to use for the display and logging
        :return: (list) The list of (product name, product_informations).
        """
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
                                "not defined in application %(application)s") %
                            { 'product': p, 'application': cfg.VARS.application} )
        
        # Construct the list of tuple containing 
        # the products name and their definition
        products_infos = src.product.get_products_infos(products, cfg)
        
        return products_infos