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
import string
import shutil
import subprocess
import fnmatch
import re

import src.debug as DBG
import src.returnCode as RCO
import src.utilsSat as UTS
from src.salomeTools import _BaseCommand
import src.system as SYSS

# Compatibility python 2/3 for input function
# input stays input for python 3 and input = raw_input for python 2
try: 
    input = raw_input
except NameError: 
    pass

########################################################################
# Command class
########################################################################
class Command(_BaseCommand):
  """
  The template command creates the sources for a SALOME module from a template.

  | Examples:
  | >> sat template --name my_product_name --template PythonComponent --target /tmp
  """
  
  name = "template"
  
  def getParser(self):
    """Define all options for command 'sat template <options>'"""
    parser = self.getParserWithHelp()
    parser.add_option('n', 'name', 'string', 'name',
        _("""\
REQUIRED: the name of the module to create.
  The name must be a single word in upper case with only alphanumeric characters.
  When generating a c++ component the module's name must be suffixed with 'CPP'."""))
    parser.add_option('t', 'template', 'string', 'template',
        _('REQUIRED: the template to use.'))
    parser.add_option('', 'target', 'string', 'target',
        _('REQUIRED: where to create the module.'))
    parser.add_option('', 'param', 'string', 'param',
        _("""\
Optional: dictionary to generate the configuration for salomeTools.
  Format is: --param param1=value1,param2=value2... (without spaces).
  Note that when using this option you must supply all the values,
       otherwise an error will be raised.""") )
    parser.add_option('', 'info', 'boolean', 'info',
        _('Optional: Get information on the template.'), False)
    return parser

  def run(self, cmd_arguments):
    """method called for command 'sat template <options>'"""
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

    msg_miss = _("The --%s argument is required\n")
    if options.template is None:
        logger.error(msg_miss % "template")
        return 1

    if options.target is None and options.info is None:
        logger.error(msg_miss % "target")
        return 1

    if "APPLICATION" in config:
        msg = _("This command does not use a product.\n")
        logger.error(msg)
        return 1

    if options.info:
        return get_template_info(config, options.template, logger)

    if options.name is None:
        logger.error(msg_miss % "name")
        return 1

    if not options.name.replace('_', '').isalnum():
        msg = _("""\
Component name must contains only alphanumeric characters and no spaces\n""")
        logger.error(msg)
        return 1

    if options.target is None:
        logger.error(msg_miss % "target")
        return 1

    target_dir = os.path.join(options.target, options.name)
    if os.path.exists(target_dir):
        msg = _("The target already exists: %s\n") % target_dir
        logger.error(msg)
        return 1

    msg = ""
    msg += _('Create sources from template\n')
    msg += '  destination = %s\n' % target_dir
    msg += '  name = %\ns' % options.name
    msg += '  template = %s\n' % options.template
    logger.info(msg)
    
    conf_values = None
    if options.param is not None:
        conf_values = {}
        for elt in options.param.split(","):
            param_def = elt.strip().split('=')
            if len(param_def) != 2:
                msg = _("Bad parameter definition: '%s'\n") % elt
                logger.error(msg)
                return 1
            conf_values[param_def[0].strip()] = param_def[1].strip()
    
    retcode = prepare_from_template(config, options.name, options.template,
        target_dir, conf_values, logger)

    if retcode == 0:
        logger.info(_("The sources were created in %s\n") % UTS.info(target_dir))
        msg = _("Do not forget to put them in your version control system.\n")
        logger.info("\n" + UTS.red(msg))
    else:    
        logger.info("\n")
    
    return retcode

class TParam:
    def __init__(self, param_def, compo_name, dico=None):
        self.default = ""
        self.prompt = ""
        self.check_method = None
        
        if isinstance(param_def, str):
            self.name = param_def
        elif isinstance(param_def, tuple):
            self.name = param_def[0]
            if len(param_def) > 1:
                if dico is not None: self.default = param_def[1] % dico
                else: self.default = param_def[1]
            if len(param_def) > 2: self.prompt = param_def[2]
            if len(param_def) > 3: self.check_method = param_def[3]
        else:
            raise Exception(_("ERROR in template parameter definition"))

        self.raw_prompt = self.prompt
        if len(self.prompt) == 0:
            self.prompt = _("value for '%s'") % self.name
        self.prompt += "? "
        if len(self.default) > 0:
            self.prompt += "[%s] " % self.default

    def check_value(self, val):
        if self.check_method is None:
            return len(val) > 0
        return len(val) > 0 and self.check_method(val)

def get_dico_param(dico, key, default):
    if dico.has_key(key):
        return dico[key]
    return default

class TemplateSettings:
    def __init__(self, compo_name, settings_file, target):
        self.compo_name = compo_name
        self.dico = None
        self.target = target

        # read the settings
        gdic, ldic = {}, {}
        execfile(settings_file, gdic, ldic)

        # check required parameters in template.info
        missing = []
        for pp in ["file_subst", "parameters"]:
            if not ldic.has_key(pp): missing.append("'%s'" % pp)
        if len(missing) > 0:
            raise Exception(
                _("Bad format in settings file! %s not defined.") % \
                ", ".join(missing) )
        
        self.file_subst = ldic["file_subst"]
        self.parameters = ldic['parameters']
        self.info = get_dico_param(ldic, "info", "").strip()
        self.pyconf = get_dico_param(ldic, "pyconf", "")
        self.post_command = get_dico_param(ldic, "post_command", "")

        # get the delimiter for the template
        self.delimiter_char = get_dico_param(ldic, "delimiter", ":sat:")

        # get the ignore filter
        self.ignore_filters = map(lambda l: l.strip(),
                                  ldic["ignore_filters"].split(','))

    def has_pyconf(self):
        return len(self.pyconf) > 0

    def get_pyconf_parameters(self):
        if len(self.pyconf) == 0:
            return []
        return re.findall("%\((?P<name>\S[^\)]*)", self.pyconf)

    ##
    # Check if the file needs to be parsed.
    def check_file_for_substitution(self, file_):
        for filter_ in self.ignore_filters:
            if fnmatch.fnmatchcase(file_, filter_):
                return False
        return True

    def check_user_values(self, values):
        if values is None:
            return
        
        # create a list of all parameters (pyconf + list))
        pnames = self.get_pyconf_parameters()
        for p in self.parameters:
            tp = TParam(p, self.compo_name)
            pnames.append(tp.name)
        
        # reduce the list
        pnames = list(set(pnames)) # remove duplicates

        known_values = ["name", "Name", "NAME", "target", self.file_subst]
        known_values.extend(values.keys())
        missing = []
        for p in pnames:
            if p not in known_values:
                missing.append(p)
        
        if len(missing) > 0:
            raise Exception(
                _("Missing parameters: %s") % ", ".join(missing) )

    def get_parameters(self, conf_values=None):
        if self.dico is not None:
            return self.dico

        self.check_user_values(conf_values)

        # create dictionary with default values
        dico = {}
        dico["name"] = self.compo_name.lower()
        dico["Name"] = self.compo_name.capitalize()
        dico["NAME"] = self.compo_name
        dico["target"] = self.target
        dico[self.file_subst] = self.compo_name
        # add user values if any
        if conf_values is not None:
            for p in conf_values.keys():
                dico[p] = conf_values[p]

        # ask user for values
        for p in self.parameters:
            tp = TParam(p, self.compo_name, dico)
            if dico.has_key(tp.name):
                continue
            
            val = ""
            while not tp.check_value(val):
                val = raw_input(tp.prompt)
                if len(val) == 0 and len(tp.default) > 0:
                    val = tp.default
            dico[tp.name] = val

        # ask for missing value for pyconf
        pyconfparam = self.get_pyconf_parameters()
        for p in filter(lambda l: not dico.has_key(l), pyconfparam):
            rep = ""
            while len(rep) == 0:
                rep = raw_input("%s? " % p)
            dico[p] = rep

        self.dico = dico
        return self.dico

def search_template(config, template):
    # search template
    template_src_dir = ""
    if os.path.isabs(template):
        if os.path.exists(template):
            template_src_dir = template
    else:
        # look in template directory
        for td in [os.path.join(config.VARS.datadir, "templates")]:
            zz = os.path.join(td, template)
            if os.path.exists(zz):
                template_src_dir = zz
                break

    if len(template_src_dir) == 0:
        raise Exception(_("Template not found: %s") % template)

    return template_src_dir


def prepare_from_template(config,
                          name,
                          template,
                          target_dir,
                          conf_values,
                          logger):
    """Prepares a module from a template."""
    template_src_dir = search_template(config, template)
    res = 0

    # copy the template
    if os.path.isfile(template_src_dir):
        logger.info(_("Extract template %s\n") % UTS.info(template))
        SYSS.archive_extract(template_src_dir, target_dir)
    else:
        logger.info(_("Copy template %s\n") % UTS.info(template))
        shutil.copytree(template_src_dir, target_dir)
    

    compo_name = name
    if name.endswith("CPP"):
        compo_name = name[:-3]

    # read settings
    settings_file = os.path.join(target_dir, "template.info")
    if not os.path.exists(settings_file):
        raise Exception(_("Settings file not found"))
    tsettings = TemplateSettings(compo_name, settings_file, target_dir)

    # first rename the files
    logger.debug(UTS.label(_("Rename files\n")))
    for root, dirs, files in os.walk(target_dir):
        for fic in files:
            ff = fic.replace(tsettings.file_subst, compo_name)
            if ff != fic:
                if os.path.exists(os.path.join(root, ff)):
                    raise Exception(
                        _("Destination file already exists: %s") % \
                        os.path.join(root, ff) )
                logger.debug("    %s -> %s\n" % (fic, ff))
                os.rename(os.path.join(root, fic), os.path.join(root, ff))

    # rename the directories
    logger.debug(UTS.label(_("Rename directories\n")))
    for root, dirs, files in os.walk(target_dir, topdown=False):
        for rep in dirs:
            dd = rep.replace(tsettings.file_subst, compo_name)
            if dd != rep:
                if os.path.exists(os.path.join(root, dd)):
                    raise Exception(
                        _("Destination directory already exists: %s") % \
                        os.path.join(root, dd) )
                logger.debug("    %s -> %s\n" % (rep, dd))
                os.rename(os.path.join(root, rep), os.path.join(root, dd))

    # ask for missing parameters
    logger.debug(UTS.label(_("Make substitution in files\n")))
    logger.debug(_("Delimiter =") + " %s\n" % tsettings.delimiter_char)
    logger.debug(_("Ignore Filters =") + " %s\n" % ', '.join(tsettings.ignore_filters))
    dico = tsettings.get_parameters(conf_values)


    class CompoTemplate(string.Template):
        """override standard string.Template class to use the desire delimiter"""
        delimiter = tsettings.delimiter_char


    # do substitution
    pathlen = len(target_dir) + 1
    for root, dirs, files in os.walk(target_dir):
        for fic in files:
            fpath = os.path.join(root, fic)
            if not tsettings.check_file_for_substitution(fpath[pathlen:]):
                logger.debug("  - %s\n" % fpath[pathlen:])
                continue
            # read the file
            m = file(fpath, 'r').read()
            # make the substitution
            template = CompoTemplate(m)
            d = template.safe_substitute(dico)
            # overwrite the file with substituted content
            changed = " "
            if d != m:
                changed = "*"
                file(fpath, 'w').write(d)
            logger.debug("  %s %s\n" % (changed, fpath[pathlen:]))

    if not tsettings.has_pyconf:
        logger.error(_("Definition for sat not found in settings file."))
    else:
        definition = tsettings.pyconf % dico
        pyconf_file = os.path.join(target_dir, name + '.pyconf')
        f = open(pyconf_file, 'w')
        f.write(definition)
        f.close
        logger.info(_("Create configuration file: ") + pyconf_file)

    if len(tsettings.post_command) > 0:
        cmd = tsettings.post_command % dico
        logger.info(_("Run post command: ") + cmd)
        
        p = subprocess.Popen(cmd, shell=True, cwd=target_dir)
        p.wait()
        res = p.returncode

    return res

def get_template_info(config, template_name, logger):
    sources = search_template(config, template_name)
    logger.info("  Template = %s\n" %  sources)

    # read settings
    tmpdir = os.path.join(config.VARS.tmp_root, "tmp_template")
    settings_file = os.path.join(tmpdir, "template.info")
    if os.path.exists(tmpdir):
        shutil.rmtree(tmpdir)
    if os.path.isdir(sources):
        shutil.copytree(sources, tmpdir)
    else:
        SYSS.archive_extract(sources, tmpdir)
        settings_file = os.path.join(tmpdir, "template.info")

    if not os.path.exists(settings_file):
        raise Exception(_("Settings file not found"))
    tsettings = TemplateSettings("NAME", settings_file, "target")
    
    skip = "\n"*3
    msg = skip
    if len(tsettings.info) == 0:
        msg += UTS.red("No information for this template.")
    else:
        msg += tsettings.info

    msg += "\n= Configuration\n"
    msg += "  file substitution key = %s\n" % tsettings.file_subst
    msg += "  substitution key = '%s'\n" % tsettings.delimiter_char
    if len(tsettings.ignore_filters) > 0:
        msg += " Ignore Filter = %s\n" % ', '.join(tsettings.ignore_filters)

    logger.info(msg)
    
    msg = skip
    msg += "= Parameters\n"
    pnames = []
    for pp in tsettings.parameters:
        tt = TParam(pp, "NAME")
        pnames.append(tt.name)
        msg += "  Name = %s\n" % tt.name
        msg += "  Prompt = %s\n" % tt.raw_prompt
        msg += "  Default value = %s\n" % tt.default

    logger.info(msg)
    
    retcode = 0
    
    msg = skip
    msg += "= Verification\n"
    if tsettings.file_subst not in pnames:
        msg += "file substitution key not defined as a parameter: %s\n" % \
                tsettings.file_subst
        retcode = 1
    
    logger.info(msg)
    
    msg = ""
    reexp = tsettings.delimiter_char.replace("$", "\$") + "{(?P<name>\S[^}]*)"
    pathlen = len(tmpdir) + 1
    for root, __, files in os.walk(tmpdir):
        for fic in files:
            fpath = os.path.join(root, fic)
            if not tsettings.check_file_for_substitution(fpath[pathlen:]):
                continue
            # read the file
            m = file(fpath, 'r').read()
            zz = re.findall(reexp, m)
            zz = list(set(zz)) # reduce
            zz = filter(lambda l: l not in pnames, zz)
            if len(zz) > 0:
                msg += "Missing definition in %s: %s\n" % \
                      ( fpath[pathlen:], ", ".join(zz) )
                retcode = 1

    logger.info(msg)
    
    if retcode == 0:
        logger.info("<OK>" + skip)
    else:
        logger.info("<KO>" + skip)


    # clean up tmp file
    shutil.rmtree(tmpdir)

    return retcode
