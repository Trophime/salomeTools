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
import shutil

import src.debug as DBG
import src.returnCode as RCO
import src.utilsSat as UTS
import src.product as PROD
from src.salomeTools import _BaseCommand
import src.system as SYSS
import src.environment as ENVI


########################################################################
# Command class
########################################################################
class Command(_BaseCommand):
  """
  The source command gets the sources of the application products
  from cvs, git or an archive.
  
  | Examples:
  | >> sat source SALOME --products KERNEL,GUI
  """
  
  name = "source"
  
  def getParser(self):
    """Define all options for command 'sat source <options>'"""
    parser = self.getParserWithHelp()
    parser.add_option('p', 'products', 'list2', 'products',
        _('Optional: products from which to get the sources. This option can be'
        ' passed several time to get the sources of several products.'))
    return parser
    
  def run(self, cmd_arguments):
    """method called for command 'sat source <options>'"""
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
    
    # check that the command has been called with an application
    UTS.check_config_has_application(config).raiseIfKo()

    # Print some informations
    logger.info(_('Getting sources of the application %s') % UTS.label(config.VARS.application))
    logger.info("  workdir = %s" % UTS.blue(config.APPLICATION.workdir))
       
    # Get the products list with products informations regarding the options
    products_infos = self.get_products_list(options, config)
    
    # Call to the function that gets all the sources
    good_result, results = get_all_product_sources(config, products_infos, logger)

    # Display the results (how much passed, how much failed, etc...)
    details = []
    nbExpected = len(products_infos)
    msgCount = "(%d/%d)" % (good_result, nbExpected)
    if good_result == nbExpected:
      status = "OK"
      msg = _("Getting sources of the application")
      logger.info("\n%s %s: <%s>.\n" % (msg, msgCount, status))
    else:
      status = "KO"
      msg = _("Some sources haven't been get")
      details = [p for p in results if (results[product] == 0 or results[product] is None)]
      details  = " ".join(details)
      logger.info("\n%s %s: <%s>.\n%s\n" % (msg, msgCount, status, details))

    return RCO.ReturnCode(status, "%s %s" % (msg, msgCount))


def get_source_for_dev(config, product_info, source_dir, logger, pad):
    """\
    Called if the product is in development mode
    
    :param config: (Config) The global configuration
    :param product_info: (Config) 
      The configuration specific to the product to be prepared
    :param source_dir: (Path)
      The Path instance corresponding to the directory where to put the sources
    :param logger: (Logger)
      The logger instance to use for the display and logging
    :param pad: (int) The gap to apply for the terminal display
    :return: (bool) True if it succeed, else False
    """
       
    # Call the function corresponding to get the sources with True checkout
    retcode = get_product_sources(config, 
                                 product_info, 
                                 True, 
                                 source_dir,
                                 logger, 
                                 pad, 
                                 checkout=True)
    # +2 because product name is followed by ': '
    logger.info("\n" + " " * (pad+2)) 
    logger.info('dev: %s ... ' % UTS.info(product_info.source_dir))
    
    return retcode

def get_source_from_git(product_info,
                        source_dir,
                        logger,
                        pad,
                        is_dev=False,
                        environ = None):
    """
    Called if the product is to be get in git mode
    
    :param product_info: (Config) 
      The configuration specific to the product to be prepared
    :param source_dir: (Path)
      The Path instance corresponding to the
      directory where to put the sources
    :param logger Logger: (Logger) 
      The logger instance to use for the display and logging
    :param pad: (int) The gap to apply for the terminal display
    :param is_dev: (bool) True if the product is in development mode
    :param environ: (src.environment.Environ)
      The environment to source when extracting.
    :return: (bool) True if it succeed, else False
    """
    # The str to display
    coflag = 'git'

    # Get the repository address. (from repo_dev key if the product is 
    # in dev mode.
    if is_dev and 'repo_dev' in product_info.git_info:
        coflag = coflag.upper()
        repo_git = product_info.git_info.repo_dev    
    else:
        repo_git = product_info.git_info.repo    
        
    # Display informations
    msg = "%s:%s" % (coflag, repo_git)
    msg += " " * (pad + 50 - len(repo_git))
    msg += " tag:%s" % product_info.git_info.tag
    msg += "%s. " % "." * (10 - len(product_info.git_info.tag))
    logger.info("\n" + msg)
    
    # Call the system function that do the extraction in git mode
    retcode = SYSS.git_extract(repo_git, product_info.git_info.tag, source_dir, logger, environ)
    return retcode

def get_source_from_archive(product_info, source_dir, logger):
    """The method called if the product is to be get in archive mode
    
    :param product_info: (Config)
      The configuration specific to 
      the product to be prepared
    :param source_dir: (Path)
      The Path instance corresponding to the directory
      where to put the sources
    :param logger: (Logger) 
      The logger instance to use for the display and logging
    :return: (bool) True if it succeed, else False
    """
    # check archive exists
    if not os.path.exists(product_info.archive_info.archive_name):
        raise Exception(_("Archive not found: '%s'") % \
                               product_info.archive_info.archive_name)

    logger.info('arc:%s ... ' % UTS.info(product_info.archive_info.archive_name))
    # Call the system function that do the extraction in archive mode
    retcode, NameExtractedDirectory = SYSS.archive_extract(
                                    product_info.archive_info.archive_name,
                                    source_dir.dir(), logger)
    
    # Rename the source directory if 
    # it does not match with product_info.source_dir
    if (NameExtractedDirectory.replace('/', '') != 
            os.path.basename(product_info.source_dir)):
        shutil.move(os.path.join(os.path.dirname(product_info.source_dir), 
                                 NameExtractedDirectory), 
                    product_info.source_dir)
    
    return retcode

def get_source_from_dir(product_info, source_dir, logger):
    
    if "dir_info" not in product_info:
        msg = _("You must put a dir_info section in the file %s.pyconf") % \
              product_info.name
        logger.error(msg)
        return False

    if "dir" not in product_info.dir_info:
        msg = _("Error: you must put a dir in the dir_info section  in the file %s.pyconf") % \
              product_info.name
        logger.error(msg)
        return False

    # check that source exists
    if not os.path.exists(product_info.dir_info.dir):
        msg = _("The dir %s defined in the file %s.pyconf does not exists") % \
                (product_info.dir_info.dir, product_info.name)
        logger.error(msg)
        return False
    
    logger.info('DIR: %s ... ' % UTS.info(product_info.dir_info.dir))
    retcode = UTS.Path(product_info.dir_info.dir).copy(source_dir) 
    return retcode
    
def get_source_from_cvs(user,
                        product_info,
                        source_dir,
                        checkout,
                        logger,
                        pad,
                        environ = None):
    """
    The method called if the product is to be get in cvs mode
    
    :param user: (str) The user to use in for the cvs command
    :param product_info: (Config) 
      The configuration specific to the product to be prepared
    :param source_dir: (Path) 
      The Path instance corresponding to the directory 
      where to put the sources
    :param checkout: (bool) If True, get the source in checkout mode
    :param logger: (Logger) 
      The logger instance to use for the display and logging
    :param pad: (int) The gap to apply for the terminal display
    :param environ: (src.environment.Environ) 
      The environment to source when extracting.
    :return: (bool) True if it succeed, else False
    """
    # Get the protocol to use in the command
    if "protocol" in product_info.cvs_info:
        protocol = product_info.cvs_info.protocol
    else:
        protocol = "pserver"
    
    # Construct the line to display
    if "protocol" in product_info.cvs_info:
        cvs_line = "%s:%s@%s:%s" % \
            (protocol, user, product_info.cvs_info.server, 
             product_info.cvs_info.product_base)
    else:
        cvs_line = "%s / %s" % (product_info.cvs_info.server, 
                                product_info.cvs_info.product_base)

    coflag = 'cvs'
    if checkout: coflag = coflag.upper()

    msg = '%s:%s' % (coflag, cvs_line)
    msg += " " * (pad + 50 - len(cvs_line))
    msg += " src:%s" % product_info.cvs_info.source
    msg += " " * (pad + 1 - len(product_info.cvs_info.source))
    msg += " tag:%s" % product_info.cvs_info.tag
                 
    # at least one '.' is visible
    msg += " %s. " % ("." * (10 - len(product_info.cvs_info.tag)))
                 
    logger.info(msg)

    # Call the system function that do the extraction in cvs mode
    retcode = SYSS.cvs_extract(protocol, user,
                                 product_info.cvs_info.server,
                                 product_info.cvs_info.product_base,
                                 product_info.cvs_info.tag,
                                 product_info.cvs_info.source,
                                 source_dir, logger, checkout, environ)
    return retcode

def get_source_from_svn(user,
                        product_info,
                        source_dir,
                        checkout,
                        logger,
                        environ = None):
    """The method called if the product is to be get in svn mode
    
    :param user: (str) The user to use in for the svn command
    :param product_info: (Config)
      The configuration specific to the product to be prepared
    :param source_dir: (Path)
      The Path instance corresponding to the directory 
      where to put the sources
    :param checkout: (boolean) 
      If True, get the source in checkout mode
    :param logger: (Logger)
      The logger instance to use for the display and logging
    :param environ: (src.environment.Environ)
      The environment to source when extracting.
    :return: (bool) True if it succeed, else False
    """
    coflag = 'svn'
    if checkout: coflag = coflag.upper()

    logger.info('%s:%s ... ' % (coflag, product_info.svn_info.repo))

    # Call the system function that do the extraction in svn mode
    retcode = SYSS.svn_extract(user, 
                               product_info.svn_info.repo, 
                               product_info.svn_info.tag,
                               source_dir, 
                               logger, 
                               checkout,
                               environ)
    return retcode

def get_product_sources(config, 
                       product_info, 
                       is_dev, 
                       source_dir,
                       logger, 
                       pad, 
                       checkout=False):
    """Get the product sources.
    
    :param config: (Config) The global configuration
    :param product_info: (Config) 
      The configuration specific to the product to be prepared
    :param is_dev: (bool) True if the product is in development mode
    :param source_dir: (Path) 
      The Path instance corresponding to the directory 
      where to put the sources
    :param logger: (Logger) 
      The logger instance to use for the display and logging
    :param pad: (int) The gap to apply for the terminal display
    :param checkout: (bool) If True, get the source in checkout mode
    :return: (bool) True if it succeed, else False
    """
    
    # Get the application environment
    logger.info(_("Set the application environment"))
    env_appli = ENVI.SalomeEnviron(config, ENVI.Environ(dict(os.environ)))
    env_appli.set_application_env(logger)
    
    # Call the right function to get sources regarding the product settings
    if not checkout and is_dev:
        return get_source_for_dev(config, product_info, source_dir, logger, pad)

    if product_info.get_source == "git":
        return get_source_from_git(product_info, source_dir, logger, pad, is_dev, env_appli)

    if product_info.get_source == "archive":
        return get_source_from_archive(product_info, source_dir, logger)

    if product_info.get_source == "dir":
        return get_source_from_dir(product_info, source_dir, logger)
    
    if product_info.get_source == "cvs":
        cvs_user = config.USER.cvs_user
        return get_source_from_cvs(cvs_user, product_info, source_dir, checkout, logger, pad, env_appli)

    if product_info.get_source == "svn":
        svn_user = config.USER.svn_user
        return get_source_from_svn(svn_user, product_info, source_dir, checkout, logger, env_appli)

    if product_info.get_source == "native":
        # skip
        msg = "<OK>" + _("\ndo nothing because the product is of type 'native'.\n")
        logger.info(msg)
        return True        

    if product_info.get_source == "fixed":
        # skip
        msg = "<OK>" + _("\ndo nothing because the product is of type 'fixed'.\n")
        logger.info(msg)
        return True  

    # if the get_source is not in [git, archive, cvs, svn, fixed, native]
    msg = _("Unknown get source method '%s' for product %s") % \
                 ( product_info.get_source, product_info.name) 
    logger.info("%s ... " % msg)
    return False

def get_all_product_sources(config, products, logger):
    """Get all the product sources.
    
    :param config: (Config) The global configuration
    :param products: (list) 
      The list of tuples (product name, product informations)
    :param logger: (Logger) 
      The logger instance to be used for the logging
    :return: (int,dict) 
      The tuple (number of success, dictionary product_name/success_fail)
    """

    # Initialize the variables that will count the fails and success
    results = dict()
    good_result = 0

    # Get the maximum name length in order to format the terminal display
    max_product_name_len = 1
    if len(products) > 0:
        max_product_name_len = max(map(lambda l: len(l), products[0])) + 4
    
    # The loop on all the products from which to get the sources
    for product_name, product_info in products:
        # get product name, product informations and the directory where to put
        # the sources
        if (not (PROD.product_is_fixed(product_info) or 
                 PROD.product_is_native(product_info))):
            source_dir = UTS.Path(product_info.source_dir)
        else:
            source_dir = UTS.Path('')

        # display and log
        logger.info('%s: ' % UTS.label(product_name))
        logger.info(' ' * (max_product_name_len - len(product_name)))
        
        # Remove the existing source directory if 
        # the product is not in development mode
        is_dev = PROD.product_is_dev(product_info)
        if source_dir.exists():
            logger.info("<OK>\n")
            msg = _("Nothing done because source directory existing yet.\n")
            logger.info(msg)
            good_result = good_result + 1
            # Do not get the sources and go to next product
            continue

        # Call to the function that get the sources for one product
        retcode = get_product_sources(config, 
                                     product_info, 
                                     is_dev, 
                                     source_dir,
                                     logger, 
                                     max_product_name_len, 
                                     checkout=False)
        
        """
        if 'no_rpath' in product_info.keys():
            if product_info.no_rpath:
                hack_no_rpath(config, product_info, logger)
        """
        
        # Check that the sources are correctly get using the files to be tested
        # in product information
        if retcode:
            rc = check_sources(product_info, logger)
            if not rc.isOk():
                # Print the missing file path
                msg = _("These required files does not exists:\n%s") % \
                       ("\n  ".join(rc.getValue()))
                logger.error(msg)
                retcode = rc

        # show results
        results[product_name] = retcode
        if retcode:
            # The case where it succeed
            res = "<OK>"
            good_result = good_result + 1
        else:
            # The case where it failed
            res = "<KO>"
        
        # print the result
        if not(PROD.product_is_fixed(product_info) or PROD.product_is_native(product_info)):
            logger.info('%s\n' % res)

    return good_result, results

def check_sources(product_info, logger):
    """
    Check that the sources are correctly get, 
    using the files to be tested in product information
    
    :param product_info: (Config)
      The configuration specific to the product to be prepared
    :param logger: (Logger) 
      The logger instance to be used for the logging
    :return: (RCO.ReturnCode) 
      OK if the files exists (or no files to test is provided).
    """
    # Get the files to test if there is any
    if not ("present_files" in product_info and  "source" in product_info.present_files):
      return RCO.ReturnCode("OK", "check_sources, nothing to check")
    
    l_files_to_be_tested = product_info.present_files.source
    for file_path in l_files_to_be_tested:
      # add source directory of the product
      path_to_test = os.path.join(product_info.source_dir, file_path)
      msg = _("File %s testing existence:" % path_to_test)
      if not os.path.exists(path_to_test):
        logger.debug("%s <KO>" % msg)
        filesKo.append(path_to_test) # check all              
      else:
        logger.debug("%s <OK>" % msg)
    if len(filesKo) != 0:
      return RCO.ReturnCode("KO", "check_sources, missing files")
    else:
      return RCO.ReturnCode("OK", "check_sources, no missing file")
    
