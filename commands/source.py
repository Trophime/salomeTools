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
from src.salomeTools import _BaseCommand

########################################################################
# Command class
########################################################################
class Command(_BaseCommand):
  """\
  The source command gets the sources of the application products
  from cvs, git or an archive.
  
  examples:
    >> sat source SALOME --products KERNEL,GUI
  """
  
  name = "sourcre"
  
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
    src.check_config_has_application( config )

    # Print some informations
    logger.write(_('Getting sources of the application %s\n') % \
                src.printcolors.printcLabel(config.VARS.application), 1)
    src.printcolors.print_value(logger, 'workdir', 
                                config.APPLICATION.workdir, 2)
    logger.write("\n", 2, False)
       
    # Get the products list with products informations regarding the options
    products_infos = self.get_products_list(options, config, logger)
    
    # Call to the function that gets all the sources
    good_result, results = get_all_product_sources(config, 
                                                  products_infos,
                                                  logger)

    # Display the results (how much passed, how much failed, etc...)
    details = []

    logger.write("\n", 2, False)
    if good_result == len(products_infos):
        res_count = "%d / %d" % (good_result, good_result)
        returnCode = RCO.ReturnCode("OK", "source "+res_count)     
    else:
        res_count = "%d / %d" % (good_result, len(products_infos))
        returnCode = RCO.ReturnCode("KO", "source "+res_count)     
        for product in results:
            if results[product] == 0 or results[product] is None:
                details.append(product)

    result = len(products_infos) - good_result

    # write results
    logger.write(_("Getting sources of the application:"), 1)
    logger.write(" " + src.printcolors.printc(status), 1, False)
    logger.write(" (%s)\n" % res_count, 1, False)

    if len(details) > 0:
        logger.write(_("Following sources haven't been get:\n"), 2)
        logger.write(" ".join(details), 2)
        logger.write("\n", 2, False)

    return returnCode


def get_source_for_dev(config, product_info, source_dir, logger, pad):
    '''The method called if the product is in development mode
    
    :param config Config: The global configuration
    :param product_info Config: The configuration specific to 
                               the product to be prepared
    :param source_dir Path: The Path instance corresponding to the 
                            directory where to put the sources
    :param logger Logger: The logger instance to use for the display and logging
    :param pad int: The gap to apply for the terminal display
    :return: True if it succeed, else False
    :rtype: boolean
    '''
       
    # Call the function corresponding to get the sources with True checkout
    retcode = get_product_sources(config, 
                                 product_info, 
                                 True, 
                                 source_dir,
                                 logger, 
                                 pad, 
                                 checkout=True)
    logger.write("\n", 3, False)
    # +2 because product name is followed by ': '
    logger.write(" " * (pad+2), 3, False) 
    
    logger.write('dev: %s ... ' % \
                 src.printcolors.printcInfo(product_info.source_dir), 3, False)
    logger.flush()
    
    return retcode

def get_source_from_git(product_info,
                        source_dir,
                        logger,
                        pad,
                        is_dev=False,
                        environ = None):
    '''The method called if the product is to be get in git mode
    
    :param product_info Config: The configuration specific to 
                               the product to be prepared
    :param source_dir Path: The Path instance corresponding to the 
                            directory where to put the sources
    :param logger Logger: The logger instance to use for the display and logging
    :param pad int: The gap to apply for the terminal display
    :param is_dev boolean: True if the product is in development mode
    :param environ src.environment.Environ: The environment to source when
                                                extracting.
    :return: True if it succeed, else False
    :rtype: boolean
    '''
    # The str to display
    coflag = 'git'

    # Get the repository address. (from repo_dev key if the product is 
    # in dev mode.
    if is_dev and 'repo_dev' in product_info.git_info:
        coflag = src.printcolors.printcHighlight(coflag.upper())
        repo_git = product_info.git_info.repo_dev    
    else:
        repo_git = product_info.git_info.repo    
        
    # Display informations
    logger.write('%s:%s' % (coflag, src.printcolors.printcInfo(repo_git)), 3, 
                 False)
    logger.write(' ' * (pad + 50 - len(repo_git)), 3, False)
    logger.write(' tag:%s' % src.printcolors.printcInfo(
                                                    product_info.git_info.tag), 
                 3,
                 False)
    logger.write(' %s. ' % ('.' * (10 - len(product_info.git_info.tag))), 3, 
                 False)
    logger.flush()
    logger.write('\n', 5, False)
    # Call the system function that do the extraction in git mode
    retcode = src.system.git_extract(repo_git,
                                 product_info.git_info.tag,
                                 source_dir, logger, environ)
    return retcode

def get_source_from_archive(product_info, source_dir, logger):
    '''The method called if the product is to be get in archive mode
    
    :param product_info Config: The configuration specific to 
                               the product to be prepared
    :param source_dir Path: The Path instance corresponding to the 
                            directory where to put the sources
    :param logger Logger: The logger instance to use for the display and logging
    :return: True if it succeed, else False
    :rtype: boolean
    '''
    # check archive exists
    if not os.path.exists(product_info.archive_info.archive_name):
        raise Exception(_("Archive not found: '%s'") % \
                               product_info.archive_info.archive_name)

    logger.write('arc:%s ... ' % \
                 src.printcolors.printcInfo(product_info.archive_info.archive_name),
                 3, False)
    logger.flush()
    # Call the system function that do the extraction in archive mode
    retcode, NameExtractedDirectory = src.system.archive_extract(
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
        msg = _("Error: you must put a dir_info section in the file %s.pyconf") % \
              product_info.name
        logger.write("\n%s\n" % src.printcolors.printcError(msg), 1)
        return False

    if "dir" not in product_info.dir_info:
        msg = _("Error: you must put a dir in the dir_info section  in the file %s.pyconf") % \
              product_info.name
        logger.write("\n%s\n" % src.printcolors.printcError(msg), 1)
        return False

    # check that source exists
    if not os.path.exists(product_info.dir_info.dir):
        msg = _("ERROR: the dir '%(1)s' defined in the file %(2)s.pyconf does not exists") % \
              {"1": product_info.dir_info.dir, "2": product_info.name}
        logger.write("\n%s\n" % src.printcolors.printcError(msg), 1)
        return False
    
    logger.write('DIR: %s ... ' % src.printcolors.printcInfo(
                                           product_info.dir_info.dir), 3)
    logger.flush()

    retcode = src.Path(product_info.dir_info.dir).copy(source_dir)
    
    return retcode
    
def get_source_from_cvs(user,
                        product_info,
                        source_dir,
                        checkout,
                        logger,
                        pad,
                        environ = None):
    '''The method called if the product is to be get in cvs mode
    
    :param user str: The user to use in for the cvs command
    :param product_info Config: The configuration specific to 
                               the product to be prepared
    :param source_dir Path: The Path instance corresponding to the 
                            directory where to put the sources
    :param checkout boolean: If True, get the source in checkout mode
    :param logger Logger: The logger instance to use for the display and logging
    :param pad int: The gap to apply for the terminal display
    :param environ src.environment.Environ: The environment to source when
                                                extracting.
    :return: True if it succeed, else False
    :rtype: boolean
    '''
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
    if checkout: coflag = src.printcolors.printcHighlight(coflag.upper())

    logger.write('%s:%s' % (coflag, src.printcolors.printcInfo(cvs_line)), 
                 3, False)
    logger.write(' ' * (pad + 50 - len(cvs_line)), 3, False)
    logger.write(' src:%s' % src.printcolors.printcInfo(product_info.cvs_info.source), 
                 3, False)
    logger.write(' ' * (pad + 1 - len(product_info.cvs_info.source)), 3, False)
    logger.write(' tag:%s' % src.printcolors.printcInfo(product_info.cvs_info.tag), 
                 3, False)
    # at least one '.' is visible
    logger.write(' %s. ' % ('.' * (10 - len(product_info.cvs_info.tag))), 
                 3, False) 
    logger.flush()
    logger.write('\n', 5, False)

    # Call the system function that do the extraction in cvs mode
    retcode = src.system.cvs_extract(protocol, user,
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
    '''The method called if the product is to be get in svn mode
    
    :param user str: The user to use in for the svn command
    :param product_info Config: The configuration specific to 
                               the product to be prepared
    :param source_dir Path: The Path instance corresponding to the 
                            directory where to put the sources
    :param checkout boolean: If True, get the source in checkout mode
    :param logger Logger: The logger instance to use for the display and logging
    :param environ src.environment.Environ: The environment to source when
                                                extracting.
    :return: True if it succeed, else False
    :rtype: boolean
    '''
    coflag = 'svn'
    if checkout: coflag = src.printcolors.printcHighlight(coflag.upper())

    logger.write('%s:%s ... ' % (coflag, src.printcolors.printcInfo(product_info.svn_info.repo)), 
                 3,  False)
    logger.flush()
    logger.write('\n', 5, False)
    # Call the system function that do the extraction in svn mode
    retcode = src.system.svn_extract(user, 
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
    '''Get the product sources.
    
    :param config Config: The global configuration
    :param product_info Config: The configuration specific to 
                               the product to be prepared
    :param is_dev boolean: True if the product is in development mode
    :param source_dir Path: The Path instance corresponding to the 
                            directory where to put the sources
    :param logger Logger: The logger instance to use for the display and logging
    :param pad int: The gap to apply for the terminal display
    :param checkout boolean: If True, get the source in checkout mode
    :return: True if it succeed, else False
    :rtype: boolean
    '''
    
    # Get the application environment
    logger.write(_("Set the application environment\n"), 5)
    env_appli = src.environment.SalomeEnviron(config,
                                      src.environment.Environ(dict(os.environ)))
    env_appli.set_application_env(logger)
    
    # Call the right function to get sources regarding the product settings
    if not checkout and is_dev:
        return get_source_for_dev(config, 
                                   product_info, 
                                   source_dir, 
                                   logger, 
                                   pad)

    if product_info.get_source == "git":
        return get_source_from_git(product_info, source_dir, logger, pad, 
                                    is_dev,env_appli)

    if product_info.get_source == "archive":
        return get_source_from_archive(product_info, source_dir, logger)

    if product_info.get_source == "dir":
        return get_source_from_dir(product_info, source_dir, logger)
    
    if product_info.get_source == "cvs":
        cvs_user = config.USER.cvs_user
        return get_source_from_cvs(cvs_user, 
                                    product_info, 
                                    source_dir, 
                                    checkout, 
                                    logger,
                                    pad,
                                    env_appli)

    if product_info.get_source == "svn":
        svn_user = config.USER.svn_user
        return get_source_from_svn(svn_user, product_info, source_dir, 
                                    checkout,
                                    logger,
                                    env_appli)

    if product_info.get_source == "native":
        # skip
        logger.write('%s  ' % src.printcolors.printc(RCO.OK_STATUS),
                     3,
                     False)
        msg = _("INFORMATION : do nothing because the product is of type 'native'.\n")
        logger.write(msg, 3)
        return True        

    if product_info.get_source == "fixed":
        # skip
        logger.write('%s  ' % src.printcolors.printc(RCO.OK_STATUS),
                     3,
                     False)
        msg = _("INFORMATION : do nothing because the product is of type 'fixed'.\n")
        logger.write(msg, 3)
        return True  

    # if the get_source is not in [git, archive, cvs, svn, fixed, native]
    logger.write(_("Unknown get source method '%(get)s' for product %(product)s") % \
                 {'get': product_info.get_source, 'product': product_info.name}, 
                 3, False)
    logger.write(" ... ", 3, False)
    logger.flush()
    return False

def get_all_product_sources(config, products, logger):
    '''Get all the product sources.
    
    :param config Config: The global configuration
    :param products List: The list of tuples (product name, product informations)
    :param logger Logger: The logger instance to be used for the logging
    :return: the tuple (number of success, dictionary product_name/success_fail)
    :rtype: (int,dict)
    '''

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
        if (not (src.product.product_is_fixed(product_info) or 
                 src.product.product_is_native(product_info))):
            source_dir = src.Path(product_info.source_dir)
        else:
            source_dir = src.Path('')

        # display and log
        logger.write('%s: ' % src.printcolors.printcLabel(product_name), 3)
        logger.write(' ' * (max_product_name_len - len(product_name)), 3, False)
        logger.write("\n", 4, False)
        
        # Remove the existing source directory if 
        # the product is not in development mode
        is_dev = src.product.product_is_dev(product_info)
        if source_dir.exists():
            logger.write('%s  ' % src.printcolors.printc(RCO.OK_STATUS),
                         3,
                         False)
            msg = _("INFORMATION : Not doing anything because the source"
                    " directory already exists.\n")
            logger.write(msg, 3)
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
        
        '''
        if 'no_rpath' in product_info.keys():
            if product_info.no_rpath:
                hack_no_rpath(config, product_info, logger)
        '''
        
        # Check that the sources are correctly get using the files to be tested
        # in product information
        if retcode:
            check_OK, wrong_path = check_sources(product_info, logger)
            if not check_OK:
                # Print the missing file path
                msg = _("The required file %s does not exists. ") % wrong_path
                logger.write(src.printcolors.printcError("\nERROR: ") + msg, 3)
                retcode = False

        # show results
        results[product_name] = retcode
        if retcode:
            # The case where it succeed
            res = RCO.OK_STATUS
            good_result = good_result + 1
        else:
            # The case where it failed
            res = RCO.KO_STATUS
        
        # print the result
        if not(src.product.product_is_fixed(product_info) or 
               src.product.product_is_native(product_info)):
            logger.write('%s\n' % src.printcolors.printc(res), 3, False)

    return good_result, results

def check_sources(product_info, logger):
    '''Check that the sources are correctly get, using the files to be tested
       in product information
    
    :param product_info Config: The configuration specific to 
                                the product to be prepared
    :return: True if the files exists (or no files to test is provided).
    :rtype: boolean
    '''
    # Get the files to test if there is any
    if ("present_files" in product_info and 
        "source" in product_info.present_files):
        l_files_to_be_tested = product_info.present_files.source
        for file_path in l_files_to_be_tested:
            # The path to test is the source directory 
            # of the product joined the file path provided
            path_to_test = os.path.join(product_info.source_dir, file_path)
            logger.write(_("\nTesting existence of file: \n"), 5)
            logger.write(path_to_test, 5)
            if not os.path.exists(path_to_test):
                return False, path_to_test
            logger.write(src.printcolors.printcSuccess(" OK\n"), 5)
    return True, ""
