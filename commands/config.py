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

import src
import src.debug as DBG
import src.returnCode as RCO
from src.salomeTools import _BaseCommand


class ConfigOpener:
    '''Class that helps to find an application pyconf 
       in all the possible directories (pathList)
    '''
    def __init__(self, pathList):
        '''Initialization
        
        :param pathList list: The list of paths where to search a pyconf.
        '''
        self.pathList = pathList

    def __call__(self, name):
        if os.path.isabs(name):
            return src.pyconf.ConfigInputStream(open(name, 'rb'))
        else:
            return src.pyconf.ConfigInputStream( 
                        open(os.path.join( self.get_path(name), name ), 'rb') )
        raise IOError(_("Configuration file '%s' not found") % name)

    def get_path( self, name ):
        '''The method that returns the entire path of the pyconf searched
        :param name str: The name of the searched pyconf.
        '''
        for path in self.pathList:
            if os.path.exists(os.path.join(path, name)):
                return path
        raise IOError(_("Configuration file '%s' not found") % name)

class ConfigManager:
    '''Class that manages the read of all the configuration files of salomeTools
    '''
    def __init__(self, datadir=None):
        pass

    def _create_vars(self, application=None, command=None, datadir=None):
        '''Create a dictionary that stores all information about machine,
           user, date, repositories, etc...
        
        :param application str: The application for which salomeTools is called.
        :param command str: The command that is called.
        :param datadir str: The repository that contain external data 
                            for salomeTools.
        :return: The dictionary that stores all information.
        :rtype: dict
        '''
        var = {}      
        var['user'] = src.architecture.get_user()
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
        src.ensure_path_exists(var['personalDir'])

        var['personal_applications_dir'] = os.path.join(var['personalDir'],
                                                        "Applications")
        src.ensure_path_exists(var['personal_applications_dir'])
        
        var['personal_products_dir'] = os.path.join(var['personalDir'],
                                                    "products")
        src.ensure_path_exists(var['personal_products_dir'])
        
        var['personal_archives_dir'] = os.path.join(var['personalDir'],
                                                    "Archives")
        src.ensure_path_exists(var['personal_archives_dir'])

        var['personal_jobs_dir'] = os.path.join(var['personalDir'],
                                                "Jobs")
        src.ensure_path_exists(var['personal_jobs_dir'])

        var['personal_machines_dir'] = os.path.join(var['personalDir'],
                                                    "Machines")
        src.ensure_path_exists(var['personal_machines_dir'])

        # read linux distributions dictionary
        distrib_cfg = src.pyconf.Config(os.path.join(var['srcDir'],
                                                      'internal_config',
                                                      'distrib.pyconf'))
        
        # set platform parameters
        dist_name = src.architecture.get_distribution(
                                            codes=distrib_cfg.DISTRIBUTIONS)
        dist_version = src.architecture.get_distrib_version(dist_name, 
                                                    codes=distrib_cfg.VERSIONS)
        dist = dist_name + dist_version
        
        var['dist_name'] = dist_name
        var['dist_version'] = dist_version
        var['dist'] = dist
        var['python'] = src.architecture.get_python_version()

        var['nb_proc'] = src.architecture.get_nb_proc()
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
        if src.architecture.is_windows() : 
            var['tmp_root'] =  os.path.expanduser('~') + os.sep + 'tmp'
        
        return var

    def get_command_line_overrides(self, options, sections):
        '''get all the overwrites that are in the command line
        
        :param options: the options from salomeTools class 
                        initialization (like -l5 or --overwrite)
        :param sections str: The config section to overwrite.
        :return: The list of all the overwrites to apply.
        :rtype: list
        '''
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
        '''get the config from all the configuration files.
        
        :param application str: The application for which salomeTools is called.
        :param options class Options: The general salomeTools
                                      options (--overwrite or -v5, for example)
        :param command str: The command that is called.
        :param datadir str: The repository that contain 
                            external data for salomeTools.
        :return: The final config.
        :rtype: class 'src.pyconf.Config'
        '''        
        
        # create a ConfigMerger to handle merge
        merger = src.pyconf.ConfigMerger()#MergeHandler())
        
        # create the configuration instance
        cfg = src.pyconf.Config()
        
        # =====================================================================
        # create VARS section
        var = self._create_vars(application=application, command=command, 
                                datadir=datadir)
        # add VARS to config
        cfg.VARS = src.pyconf.Mapping(cfg)
        for variable in var:
            cfg.VARS[variable] = var[variable]
        
        # apply overwrite from command line if needed
        for rule in self.get_command_line_overrides(options, ["VARS"]):
            exec('cfg.' + rule) # this cannot be factorized because of the exec
        
        # =====================================================================
        # Load INTERNAL config
        # read src/internal_config/salomeTools.pyconf
        src.pyconf.streamOpener = ConfigOpener([
                            os.path.join(cfg.VARS.srcDir, 'internal_config')])
        try:
            internal_cfg = src.pyconf.Config(open(os.path.join(cfg.VARS.srcDir, 
                                    'internal_config', 'salomeTools.pyconf')))
        except src.pyconf.ConfigError as e:
            raise src.SatException(_("Error in configuration file:"
                                     " salomeTools.pyconf\n  %(error)s") % \
                                   {'error': str(e) })
        
        merger.merge(cfg, internal_cfg)

        # apply overwrite from command line if needed
        for rule in self.get_command_line_overrides(options, ["INTERNAL"]):
            exec('cfg.' + rule) # this cannot be factorized because of the exec        
               
        # =====================================================================
        # Load LOCAL config file
        # search only in the data directory
        src.pyconf.streamOpener = ConfigOpener([cfg.VARS.datadir])
        try:
            local_cfg = src.pyconf.Config(open(os.path.join(cfg.VARS.datadir, 
                                                           'local.pyconf')),
                                         PWD = ('LOCAL', cfg.VARS.datadir) )
        except src.pyconf.ConfigError as e:
            raise src.SatException(_("Error in configuration file: "
                                     "local.pyconf\n  %(error)s") % \
                {'error': str(e) })
        except IOError as error:
            e = str(error)
            raise src.SatException( e );
        merger.merge(cfg, local_cfg)

        # When the key is "default", put the default value
        if cfg.LOCAL.base == "default":
            cfg.LOCAL.base = os.path.abspath(
                                        os.path.join(cfg.VARS.salometoolsway,
                                                     "..",
                                                     "BASE"))
        if cfg.LOCAL.workdir == "default":
            cfg.LOCAL.workdir = os.path.abspath(
                                        os.path.join(cfg.VARS.salometoolsway,
                                                     ".."))
        if cfg.LOCAL.log_dir == "default":
            cfg.LOCAL.log_dir = os.path.abspath(
                                        os.path.join(cfg.VARS.salometoolsway,
                                                     "..",
                                                     "LOGS"))

        if cfg.LOCAL.archive_dir == "default":
            cfg.LOCAL.archive_dir = os.path.abspath(
                                        os.path.join(cfg.VARS.salometoolsway,
                                                     "..",
                                                     "ARCHIVES"))

        # apply overwrite from command line if needed
        for rule in self.get_command_line_overrides(options, ["LOCAL"]):
            exec('cfg.' + rule) # this cannot be factorized because of the exec
        
        # =====================================================================
        # Load the PROJECTS
        projects_cfg = src.pyconf.Config()
        projects_cfg.addMapping("PROJECTS",
                                src.pyconf.Mapping(projects_cfg),
                                "The projects\n")
        projects_cfg.PROJECTS.addMapping("projects",
                                src.pyconf.Mapping(cfg.PROJECTS),
                                "The projects definition\n")
        
        for project_pyconf_path in cfg.PROJECTS.project_file_paths:
            if not os.path.exists(project_pyconf_path):
                msg = _("WARNING: The project file %s cannot be found. "
                        "It will be ignored\n") % project_pyconf_path
                sys.stdout.write(msg)
                continue
            project_name = os.path.basename(project_pyconf_path)[:-len(".pyconf")]
            try:
                project_pyconf_dir = os.path.dirname(project_pyconf_path)
                project_cfg = src.pyconf.Config(open(project_pyconf_path),
                                                PWD=("", project_pyconf_dir))
            except Exception as e:
                msg = _("ERROR: Error in configuration file: %(file_path)s\n  %(error)s\n") % \
                       {'file_path' : project_pyconf_path, 'error': str(e) }
                sys.stdout.write(msg)
                continue
            projects_cfg.PROJECTS.projects.addMapping(project_name,
                             src.pyconf.Mapping(projects_cfg.PROJECTS.projects),
                             "The %s project\n" % project_name)
            projects_cfg.PROJECTS.projects[project_name]=project_cfg
            projects_cfg.PROJECTS.projects[project_name]["file_path"] = \
                                                        project_pyconf_path
                   
        merger.merge(cfg, projects_cfg)

        # apply overwrite from command line if needed
        for rule in self.get_command_line_overrides(options, ["PROJECTS"]):
            exec('cfg.' + rule) # this cannot be factorized because of the exec
        
        # =====================================================================
        # Create the paths where to search the application configurations, 
        # the product configurations, the products archives, 
        # the jobs configurations and the machines configurations
        cfg.addMapping("PATHS", src.pyconf.Mapping(cfg), "The paths\n")
        cfg.PATHS["APPLICATIONPATH"] = src.pyconf.Sequence(cfg.PATHS)
        cfg.PATHS.APPLICATIONPATH.append(cfg.VARS.personal_applications_dir, "")
        
        cfg.PATHS["PRODUCTPATH"] = src.pyconf.Sequence(cfg.PATHS)
        cfg.PATHS.PRODUCTPATH.append(cfg.VARS.personal_products_dir, "")
        cfg.PATHS["ARCHIVEPATH"] = src.pyconf.Sequence(cfg.PATHS)
        cfg.PATHS.ARCHIVEPATH.append(cfg.VARS.personal_archives_dir, "")
        cfg.PATHS["JOBPATH"] = src.pyconf.Sequence(cfg.PATHS)
        cfg.PATHS.JOBPATH.append(cfg.VARS.personal_jobs_dir, "")
        cfg.PATHS["MACHINEPATH"] = src.pyconf.Sequence(cfg.PATHS)
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
            src.pyconf.streamOpener = ConfigOpener(cp)
            do_merge = True
            try:
                application_cfg = src.pyconf.Config(application + '.pyconf')
            except IOError as e:
                raise src.SatException(_("%s, use 'config --list' to get the"
                                         " list of available applications.") % e)
            except src.pyconf.ConfigError as e:
                if (not ('-e' in parser.parse_args()[1]) 
                                         or ('--edit' in parser.parse_args()[1]) 
                                         and command == 'config'):
                    raise src.SatException(
                        _("Error in configuration file: (1)s.pyconf\n  %(2)s") % \
                        { 'application': application, 'error': str(e) } )
                else:
                    sys.stdout.write(src.printcolors.printcWarning(
                        "There is an error in the file %s.pyconf.\n" % \
                        cfg.VARS.application))
                    do_merge = False
            except Exception as e:
                if ( not('-e' in parser.parse_args()[1]) or
                     ('--edit' in parser.parse_args()[1]) and
                     command == 'config' ):
                    sys.stdout.write(src.printcolors.printcWarning("%s\n" % str(e)))
                    raise src.SatException(
                        _("Error in configuration file: %s.pyconf\n") % application )
                else:
                    sys.stdout.write(src.printcolors.printcWarning(
                        "ERROR: in file %s.pyconf. Opening the file with the default viewer\n" % \
                        cfg.VARS.application))
                    sys.stdout.write("\n%s\n" % src.printcolors.printcWarning(str(e)))
                    do_merge = False
        
            else:
                cfg['open_application'] = 'yes'

        # =====================================================================
        # Load product config files in PRODUCTS section
        products_cfg = src.pyconf.Config()
        products_cfg.addMapping("PRODUCTS",
                                src.pyconf.Mapping(products_cfg),
                                "The products\n")
        if application is not None:
            src.pyconf.streamOpener = ConfigOpener(cfg.PATHS.PRODUCTPATH)
            for product_name in application_cfg.APPLICATION.products.keys():
                # Loop on all files that are in softsDir directory
                # and read their config
                product_file_name = product_name + ".pyconf"
                product_file_path = src.find_file_in_lpath(product_file_name, cfg.PATHS.PRODUCTPATH)
                if product_file_path:
                    products_dir = os.path.dirname(product_file_path)
                    try:
                        prod_cfg = src.pyconf.Config(open(product_file_path),
                                                     PWD=("", products_dir))
                        prod_cfg.from_file = product_file_path
                        products_cfg.PRODUCTS[product_name] = prod_cfg
                    except Exception as e:
                        msg = _(
                            "WARNING: Error in configuration file: %(prod)s\n  %(error)s" % \
                            {'prod' :  product_name, 'error': str(e) })
                        sys.stdout.write(msg)
            
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
        user_cfg = src.pyconf.Config(open(user_cfg_file))
        merger.merge(cfg, user_cfg)

        # apply overwrite from command line if needed
        for rule in self.get_command_line_overrides(options, ["USER"]):
            exec('cfg.' + rule) # this cannot be factorize because of the exec
        
        return cfg

    def set_user_config_file(self, config):
        '''Set the user config file name and path.
        If necessary, build it from another one or create it from scratch.
        
        :param config class 'src.pyconf.Config': The global config 
                                                 (containing all pyconf).
        '''
        # get the expected name and path of the file
        self.config_file_name = 'SAT.pyconf'
        self.user_config_file_path = os.path.join(config.VARS.personalDir,
                                                   self.config_file_name)
        
        # if pyconf does not exist, create it from scratch
        if not os.path.isfile(self.user_config_file_path): 
            self.create_config_file(config)
    
    def create_config_file(self, config):
        '''This method is called when there are no user config file. 
           It build it from scratch.
        
        :param config class 'src.pyconf.Config': The global config.
        :return: the config corresponding to the file created.
        :rtype: config class 'src.pyconf.Config'
        '''
        
        cfg_name = self.get_user_config_file()

        user_cfg = src.pyconf.Config()
        #
        user_cfg.addMapping('USER', src.pyconf.Mapping(user_cfg), "")

        user_cfg.USER.addMapping('cvs_user', config.VARS.user,
            "This is the user name used to access salome cvs base.\n")
        user_cfg.USER.addMapping('svn_user', config.VARS.user,
            "This is the user name used to access salome svn base.\n")
        user_cfg.USER.addMapping('output_verbose_level', 3,
            "This is the default output_verbose_level you want."
            " 0=>no output, 5=>debug.\n")
        user_cfg.USER.addMapping('publish_dir', 
                                 os.path.join(os.path.expanduser('~'),
                                 'websupport', 
                                 'satreport'), 
                                 "")
        user_cfg.USER.addMapping('editor',
                                 'vi', 
                                 "This is the editor used to "
                                 "modify configuration files\n")
        user_cfg.USER.addMapping('browser', 
                                 'firefox', 
                                 "This is the browser used to "
                                 "read html documentation\n")
        user_cfg.USER.addMapping('pdf_viewer', 
                                 'evince', 
                                 "This is the pdf_viewer used "
                                 "to read pdf documentation\n")
# CNC 25/10/17 : plus nécessaire a priori
#        user_cfg.USER.addMapping("base",
#                                 src.pyconf.Reference(
#                                            user_cfg,
#                                            src.pyconf.DOLLAR,
#                                            'workdir  + $VARS.sep + "BASE"'),
#                                 "The products installation base (could be "
#                                 "ignored if this key exists in the local.pyconf"
#                                 " file of salomTools).\n")
               
        # 
        src.ensure_path_exists(config.VARS.personalDir)
        src.ensure_path_exists(os.path.join(config.VARS.personalDir, 
                                            'Applications'))

        f = open(cfg_name, 'w')
        user_cfg.__save__(f)
        f.close()

        return user_cfg   

    def get_user_config_file(self):
        '''Get the user config file
        :return: path to the user config file.
        :rtype: str
        '''
        if not self.user_config_file_path:
            raise src.SatException(
                _("Error in get_user_config_file: missing user config file path") )
        return self.user_config_file_path     

def check_path(path, ext=[]):
    '''Construct a text with the input path and "not found" if it does not
       exist.
    
    :param path Str: the path to check.
    :param ext List: An extension. Verify that the path extension 
                     is in the list
    :return: The string of the path with information
    :rtype: Str
    '''
    # check if file exists
    if not os.path.exists(path):
        return "'%s' %s" % (path, src.printcolors.printcError(_("** not found")))

    # check extension
    if len(ext) > 0:
        fe = os.path.splitext(path)[1].lower()
        if fe not in ext:
            return "'%s' %s" % (path, src.printcolors.printcError(_("** bad extension")))

    return path

def show_product_info(config, name, logger):
    '''Display on the terminal and logger information about a product.
    
    :param config Config: the global configuration.
    :param name Str: The name of the product
    :param logger Logger: The logger instance to use for the display
    '''
    
    logger.write(_("%s is a product\n") % src.printcolors.printcLabel(name), 2)
    pinfo = src.product.get_product_config(config, name)
    
    if "depend" in pinfo:
        src.printcolors.print_value(logger, 
                                    "depends on", 
                                    ', '.join(pinfo.depend), 2)

    if "opt_depend" in pinfo:
        src.printcolors.print_value(logger, 
                                    "optional", 
                                    ', '.join(pinfo.opt_depend), 2)

    # information on pyconf
    logger.write("\n", 2)
    logger.write(src.printcolors.printcLabel("configuration:") + "\n", 2)
    if "from_file" in pinfo:
        src.printcolors.print_value(logger, 
                                    "pyconf file path", 
                                    pinfo.from_file, 
                                    2)
    if "section" in pinfo:
        src.printcolors.print_value(logger, 
                                    "section", 
                                    pinfo.section, 
                                    2)

    # information on prepare
    logger.write("\n", 2)
    logger.write(src.printcolors.printcLabel("prepare:") + "\n", 2)

    is_dev = src.product.product_is_dev(pinfo)
    method = pinfo.get_source
    if is_dev:
        method += " (dev)"
    src.printcolors.print_value(logger, "get method", method, 2)

    if method == 'cvs':
        src.printcolors.print_value(logger, "server", pinfo.cvs_info.server, 2)
        src.printcolors.print_value(logger, "base module",
                                    pinfo.cvs_info.module_base, 2)
        src.printcolors.print_value(logger, "source", pinfo.cvs_info.source, 2)
        src.printcolors.print_value(logger, "tag", pinfo.cvs_info.tag, 2)

    elif method == 'svn':
        src.printcolors.print_value(logger, "repo", pinfo.svn_info.repo, 2)

    elif method == 'git':
        src.printcolors.print_value(logger, "repo", pinfo.git_info.repo, 2)
        src.printcolors.print_value(logger, "tag", pinfo.git_info.tag, 2)

    elif method == 'archive':
        src.printcolors.print_value(logger, 
                                    "get from", 
                                    check_path(pinfo.archive_info.archive_name), 
                                    2)

    if 'patches' in pinfo:
        for patch in pinfo.patches:
            src.printcolors.print_value(logger, "patch", check_path(patch), 2)

    if src.product.product_is_fixed(pinfo):
        src.printcolors.print_value(logger, "install_dir", 
                                    check_path(pinfo.install_dir), 2)

    if src.product.product_is_native(pinfo) or src.product.product_is_fixed(pinfo):
        return
    
    # information on compilation
    if src.product.product_compiles(pinfo):
        logger.write("\n", 2)
        logger.write(src.printcolors.printcLabel("compile:") + "\n", 2)
        src.printcolors.print_value(logger, 
                                    "compilation method", 
                                    pinfo.build_source, 
                                    2)
        
        if pinfo.build_source == "script" and "compil_script" in pinfo:
            src.printcolors.print_value(logger, 
                                        "Compilation script", 
                                        pinfo.compil_script, 
                                        2)
        
        if 'nb_proc' in pinfo:
            src.printcolors.print_value(logger, "make -j", pinfo.nb_proc, 2)
    
        src.printcolors.print_value(logger, 
                                    "source dir", 
                                    check_path(pinfo.source_dir), 
                                    2)
        if 'install_dir' in pinfo:
            src.printcolors.print_value(logger, 
                                        "build dir", 
                                        check_path(pinfo.build_dir), 
                                        2)
            src.printcolors.print_value(logger, 
                                        "install dir", 
                                        check_path(pinfo.install_dir), 
                                        2)
        else:
            logger.write("  %s\n" % src.printcolors.printcWarning(_("no install dir")) , 2)
    else:
        logger.write("\n", 2)
        msg = _("This product does not compile")
        logger.write("%s\n" % msg, 2)

    # information on environment
    logger.write("\n", 2)
    logger.write(src.printcolors.printcLabel("environ :") + "\n", 2)
    if "environ" in pinfo and "env_script" in pinfo.environ:
        src.printcolors.print_value(logger, 
                                    "script", 
                                    check_path(pinfo.environ.env_script), 
                                    2)

    zz = src.environment.SalomeEnviron(config, 
                                       src.fileEnviron.ScreenEnviron(logger), 
                                       False)
    zz.set_python_libdirs()
    zz.set_a_product(name, logger)
        
def show_patchs(config, logger):
    '''Prints all the used patchs in the application.
    
    :param config Config: the global configuration.
    :param logger Logger: The logger instance to use for the display
    '''
    len_max = max([len(p) for p in config.APPLICATION.products]) + 2
    for product in config.APPLICATION.products:
        product_info = src.product.get_product_config(config, product)
        if src.product.product_has_patches(product_info):
            logger.write("%s: " % product, 1)
            logger.write(src.printcolors.printcInfo(
                                            " " * (len_max - len(product) -2) +
                                            "%s\n" % product_info.patches[0]),
                         1)
            if len(product_info.patches) > 1:
                for patch in product_info.patches[1:]:
                    logger.write(src.printcolors.printcInfo(len_max*" " +
                                                            "%s\n" % patch), 1)
            logger.write("\n", 1)

def print_value(config, path, show_label, logger, level=0, show_full_path=False):
    '''Prints a value from the configuration. Prints recursively the values 
       under the initial path.
    
    :param config class 'src.pyconf.Config': The configuration 
                                             from which the value is displayed.
    :param path str : the path in the configuration of the value to print.
    :param show_label boolean: if True, do a basic display. 
                               (useful for bash completion)
    :param logger Logger: the logger instance
    :param level int: The number of spaces to add before display.
    :param show_full_path :
    '''            
    
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
        logger.write(tab_level)
        logger.write("%s: ERROR %s\n" % (src.printcolors.printcLabel(vname), 
                                         src.printcolors.printcError(str(e))))
        return

    # in this case, display only the value
    if show_label:
        logger.write(tab_level)
        logger.write("%s: " % src.printcolors.printcLabel(vname))

    # The case where the value has under values, 
    # do a recursive call to the function
    if dir(val).__contains__('keys'):
        if show_label: logger.write("\n")
        for v in sorted(val.keys()):
            print_value(config, path + '.' + v, show_label, logger, level + 1)
    elif val.__class__ == src.pyconf.Sequence or isinstance(val, list): 
        # in this case, value is a list (or a Sequence)
        if show_label: logger.write("\n")
        index = 0
        for v in val:
            print_value(config, path + "[" + str(index) + "]", 
                        show_label, logger, level + 1)
            index = index + 1
    else: # case where val is just a str
        logger.write("%s\n" % val)
        
def print_debug(config, aPath, show_label, logger, level=0, show_full_path=False):
    """
    logger output for debugging a config/pyconf
    lines contains:
       path : expression --> 'evaluation'
    example:
      .PROJECTS.projects.salome.project_path : $PWD --> '/volatile/wambeke/SAT5/SAT5_S840_MATIX24/SAT_SALOME'
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
    logger.write(res)
    return

def get_config_children(config, args):
    '''Gets the names of the children of the given parameter.
       Useful only for completion mechanism
    
    :param config Config: The configuration where to read the values
    :param args: The path in the config from which get the keys
    '''
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


########################################################################
# Command class for command 'sat config etc.'
########################################################################
class Command(_BaseCommand):
  
  def getParser(self):
    # Define all possible option for config command :  sat config <options>
    parser = src.options.Options()
    parser.add_option('v', 'value', 'string', 'value',
        _("Optional: print the value of CONFIG_VARIABLE."))
    parser.add_option('d', 'debug', 'string', 'debug',
        _("Optional: print the debugging value of CONFIG_VARIABLE."))
    parser.add_option('e', 'edit', 'boolean', 'edit',
        _("Optional: edit the product configuration file."))
    parser.add_option('i', 'info', 'string', 'info',
        _("Optional: get information on a product."))
    parser.add_option('l', 'list', 'boolean', 'list',
        _("Optional: list all available applications."))
    parser.add_option('', 'show_patchs', 'boolean', 'show_patchs',
        _("Optional: synthetic view of all patches used in the application"))
    parser.add_option('c', 'copy', 'boolean', 'copy',
        _("""Optional: copy a config file (.pyconf) to the personal config files directory.
    \tWarning: the included files are not copied.
    \tIf a name is given the new config file takes the given name."""))
    parser.add_option('n', 'no_label', 'boolean', 'no_label',
        _("Internal use: do not print labels, Works only with --value and --list."))
    parser.add_option('', 'completion', 'boolean', 'completion',
        _("Internal use: print only keys, works only with --value."))
    parser.add_option('s', 'schema', 'boolean', 'schema',
        _("Internal use."))
    return parser

  def description(self):
    '''method that is called when salomeTools is called with --help option.
    
    :return: The text to display for the config command description.
    :rtype: str
    '''
    return _("""\
The config command allows manipulation and operation on config files.

example:
>> sat config SALOME-master --info ParaView""")
        

  def run(self, args):
      '''method that is called when salomeTools is called with config parameter.
      '''
      runner = self.getRunner()
      config = self.getConfig()
      logger = self.getLogger()
  
      # Parse the options
      (options, argsc) = self.parse_args(args)

      # Only useful for completion mechanism : print the keys of the config
      if options.schema:
          get_config_children(config, args)
          return RCO.ReturnCode("OK", "completion mechanism")
      
      # case : print a value of the config
      if options.value:
          if options.value == ".":
              # if argument is ".", print all the config
              for val in sorted(config.keys()):
                  print_value(config, val, not options.no_label, logger)
          else:
              print_value(config, options.value, not options.no_label, logger, 
                          level=0, show_full_path=False)

      if options.debug:
          print_debug(config, str(options.debug), not options.no_label, logger, 
                      level=0, show_full_path=False)
      
      # case : edit user pyconf file or application file
      elif options.edit:
          editor = config.USER.editor
          if ('APPLICATION' not in config and
              'open_application' not in config): # edit user pyconf
              usercfg = os.path.join(config.VARS.personalDir, 'SAT.pyconf')
              logger.write(_("Opening %s\n") % usercfg, 3)
              src.system.show_in_editor(editor, usercfg, logger)
          else:
              # search for file <application>.pyconf and open it
              for path in config.PATHS.APPLICATIONPATH:
                  pyconf_path = os.path.join(path, config.VARS.application + ".pyconf")
                  if os.path.exists(pyconf_path):
                      logger.write(_("Opening %s\n") % pyconf_path, 3)
                      src.system.show_in_editor(editor, pyconf_path, logger)
                      break
      
      # case : give information about the product in parameter
      elif options.info:
          src.check_config_has_application(config)
          if options.info in config.APPLICATION.products:
              show_product_info(config, options.info, logger)
              return RCO.ReturnCode("OK", "options.info")
          raise src.SatException(
              _("%(product_name)s is not a product of %(application_name)s.") % \
              {'product_name' : options.info, 'application_name' : config.VARS.application} )
      
      # case : copy an existing <application>.pyconf 
      # to ~/.salomeTools/Applications/LOCAL_<application>.pyconf
      elif options.copy:
          # product is required
          src.check_config_has_application( config )
  
          # get application file path 
          source = config.VARS.application + '.pyconf'
          source_full_path = ""
          for path in config.PATHS.APPLICATIONPATH:
              # ignore personal directory
              if path == config.VARS.personalDir:
                  continue
              # loop on all directories that can have pyconf applications
              zz = os.path.join(path, source)
              if os.path.exists(zz):
                  source_full_path = zz
                  break
  
          if len(source_full_path) == 0:
              raise src.SatException(
                  _("Config file for product %s not found\n") % source )
          else:
              if len(args) > 0:
                  # a name is given as parameter, use it
                  dest = args[0]
              elif 'copy_prefix' in config.INTERNAL.config:
                  # use prefix
                  dest = (config.INTERNAL.config.copy_prefix 
                          + config.VARS.application)
              else:
                  # use same name as source
                  dest = config.VARS.application
                  
              # the full path
              dest_file = os.path.join(
                  config.VARS.personalDir, 'Applications', dest + '.pyconf' )
              if os.path.exists(dest_file):
                  raise src.SatException(
                      _("A personal application '%s' already exists") % dest )
              
              # perform the copy
              shutil.copyfile(source_full_path, dest_file)
              logger.write(_("%s has been created.\n") % dest_file)
      
      # case : display all the available pyconf applications
      elif options.list:
          lproduct = list()
          # search in all directories that can have pyconf applications
          for path in config.PATHS.APPLICATIONPATH:
              # print a header
              if not options.no_label:
                  logger.write("------ %s\n" % src.printcolors.printcHeader(path))
  
              if not os.path.exists(path):
                  logger.write(src.printcolors.printcError(
                      _("Directory not found")) + "\n" )
              else:
                  for f in sorted(os.listdir(path)):
                      # ignore file that does not ends with .pyconf
                      if not f.endswith('.pyconf'):
                          continue
  
                      appliname = f[:-len('.pyconf')]
                      if appliname not in lproduct:
                          lproduct.append(appliname)
                          if path.startswith(config.VARS.personalDir) \
                                      and not options.no_label:
                              logger.write("%s*\n" % appliname)
                          else:
                              logger.write("%s\n" % appliname)
                              
              logger.write("\n")

      # case : give a synthetic view of all patches used in the application
      elif options.show_patchs:
          src.check_config_has_application(config)
          # Print some informations
          logger.write(_('Show the patchs of application %s\n') % \
                       src.printcolors.printcLabel(config.VARS.application), 3)
          logger.write("\n", 2, False)
          show_patchs(config, logger)
      
      # case: print all the products name of the application (internal use for completion)
      elif options.completion:
          for product_name in config.APPLICATION.products.keys():
              logger.write("%s\n" % product_name)
            
      return RCO.ReturnCode("OK")
