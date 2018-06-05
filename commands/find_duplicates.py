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


import src.debug as DBG
import src.returnCode as RCO
import src.utilsSat as UTS
import src.product as PROD
from src.salomeTools import _BaseCommand


default_extension_ignored = \
  'html png txt js xml cmake gif m4 in pyo pyc doctree css'.split()

default_files_ignored = \
  '__init__.py Makefile.am VERSION build_configure README AUTHORS NEWS COPYING ChangeLog'.split()

default_directories_ignored = []


########################################################################
# Command class
########################################################################
class Command(_BaseCommand):
  """
  The find_duplicates command search recursively for all duplicates files
  in INSTALL directory (or the optionally given directory) and 
  prints the found files to the terminal.
  
  | Examples:
  | >> sat find_duplicates --path /tmp
  """
  
  name = "find_duplicates"
  
  def getParser(self):
    """Define all options for command 'sat find_duplicates <options>'"""
    parser = self.getParserWithHelp()
    parser.add_option(
        "s",
        "sources",
        "boolean",
        "sources",
        _("Search the duplicate files in the SOURCES directory.") )
    parser.add_option(
        "p",
        "path",
        "list2",
        "path",
        _("Optional: Search the duplicate files in the given directory paths.") )
    parser.add_option(
        "",
        "exclude-file",
        "list2",
        "exclude_file",
        _("Optional: Override the default list of filtered files.") )
    parser.add_option(
        "",
        "exclude-extension",
        "list2",
        "exclude_extension",
        _("Optional: Override the default list of filtered extensions.") )
    parser.add_option(
        "",
        "exclude-path",
        "list2",
        "exclude_path",
        _("Optional: Override the default list of filtered paths.") )
    return parser

  def run(self, cmd_arguments):
    """method called for command 'sat find_duplicates <options>'"""
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
  
    # Determine the directory path where to search 
    # for duplicates files regarding the options
    if options.path:
        l_dir_path = options.path
    else:
        UTS.check_config_has_application(config).raiseIfKo()
        cfg_APP = config.APPLICATION
        if options.sources:
            l_dir_path = [os.path.join(cfg_APP.workdir, "SOURCES")]
        else:
            # find all installation paths
            all_products = cfg_APP.products.keys()
            l_product_cfg = PROD.get_products_infos(all_products, config)
            l_dir_path = [pi.install_dir for tmp, pi in l_product_cfg]
    
    # Get the files to ignore during the searching
    files_ignored = default_files_ignored
    if options.exclude_file:
        files_ignored = options.exclude_file

    # Get the extension to ignore during the searching
    extension_ignored = default_extension_ignored
    if options.exclude_extension:
        extension_ignored = options.exclude_extension

    # Get the directory paths to ignore during the searching
    directories_ignored = default_directories_ignored
    if options.exclude_path:
        directories_ignored = options.exclude_path
    
    # Check the directories
    l_path = UTS.deepcopy_list(l_dir_path)
    l_dir_path = []
    for dir_path in l_path:
        if not(os.path.isdir(dir_path)):
            msg = _("%s does not exists or is not a directory path: it will be ignored" %
                  dir_path)
            logger.warning("%s\n" % msg)
            continue
        l_dir_path.append(dir_path)
            
    
    # Display some information
    info = [(_("Directories"), "\n".join(l_dir_path)),
            (_("Ignored files"), files_ignored),
            (_("Ignored extensions"), extension_ignored),
            (_("Ignored directories"), directories_ignored)
           ]
    logger.info(UTS.formatTuples(info))
    
    # Get all the files and paths
    logger.info(_("Store all file paths ... "), 3)
    dic, fic = list_directory(l_dir_path,
                              extension_ignored,
                              files_ignored,
                              directories_ignored)  
    logger.info("<OK>\n")
    
    # Eliminate all the singletons
    len_fic = len(fic)
    range_fic = range(0,len_fic)
    range_fic.reverse()
    my_bar = Progress_bar(_('Eliminate the files that are not duplicated'),
                          0,
                          len_fic,
                          logger,
                          length = 50)
    for i in range_fic:
        my_bar.display_value_progression(len_fic - i)
        if fic.count(fic[i])==1:
            fic.remove(fic[i])
            dic.remove(dic[i])

    # Format the resulting variable to get a dictionary
    logger.info(_("\n\nCompute the dict for file -> list of paths ... "))
    fic.sort()
    len_fic = len(fic)
    rg_fic = range(0,len_fic)
    rg_fic.reverse()
    for i in rg_fic:
        if fic[i-1] != fic[i]:
            fic.remove(fic[i])

    dic_fic_paths = {}
    for fichier in fic:
        the_file = fichier[0]
        l_path = []
        for fic_path in dic:
            if fic_path[0] == the_file:
                l_path.append(fic_path[1])
        dic_fic_paths[the_file] = l_path
    
    logger.info("<OK>\n")

    # End the execution if no duplicates were found
    if len(dic_fic_paths) == 0:
        logger.info(_("No duplicate files found.\n"))
        return 0

    # Check that there are no singletons in the result (it would be a bug)
    for elem in dic_fic_paths:
        if len(dic_fic_paths[elem])<2:
            logger.warning(_("Element %s has not more than two paths.\n") % elem)


    # Display the results
    logger.info(_('\nResults:\n\n'))
    max_file_name_length = max(map(lambda l: len(l), dic_fic_paths.keys()))
    for fich in dic_fic_paths:
        sp = " " * (max_file_name_length - len(fich))
        msg = UTS.label(fich) + sp
        for rep in dic_fic_paths[fich]:
            msg += rep + " "
        logger.info(msg + "\n")

    return RCO.ReturnCode("OK", "find_duplicates command done")


def list_directory(lpath, extension_ignored, files_ignored, directories_ignored):
    """Make the list of all files and paths that are not filtered 
    
    :param lpath: (list) 
      The list of path to of the directories where to  search for duplicates
    :param extension_ignored: (list) The list of extensions to ignore
    :param files_ignored: (list) The list of files to ignore
    :param directories_ignored: (list) 
      The list of directory paths to ignore
    :return: (list, list) 
      files_arb_out is the list of [file, path] 
      and files_out is is the list of files
    """
    files_out = []
    files_arb_out=[]
    for path in lpath:
        for root, __, files in os.walk(path):  
            for fic in files:
                extension = fic.split('.')[-1]   
                if (extension not in extension_ignored and 
                                                      fic not in files_ignored):
                    in_ignored_dir = False
                    for rep in directories_ignored:
                        if rep in root:
                            in_ignored_dir = True                
                    if not in_ignored_dir:
                        files_out.append([fic])              
                        files_arb_out.append([fic, root])
    return files_arb_out, files_out

def format_list_of_str(l_str):
    """Make a list from a string
    
    :param l_str: (list or str) The variable to format
    :return: (list) the formatted variable
    """
    if not isinstance(l_str, list):
        return l_str
    return ",".join(l_str)

class Progress_bar:
    """
    Create a progress bar in the terminal
    """
    def __init__(self, name, valMin, valMax, logger, length = 50):
        """Initialization of the progress bar.
        
        :param name: (str) The name of the progress bar
        :param valMin: (float) the minimum value of the variable
        :param valMax: (float) the maximum value of the variable
        :param logger: (Logger) the logger instance
        :param length: (int) the length of the progress bar
        """
        self.name = name
        self.valMin = valMin
        self.valMax = valMax
        self.length = length
        self.logger = logger
        if (self.valMax - self.valMin) <= 0 or length <= 0:
            out_err = _('Wrong init values for the progress bar\n')
            raise Exception(out_err)
        
    def display_value_progression(self,val):
        """Display the progress bar.
        
        :param val: (float) val must be between valMin and valMax.
        """
        if val < self.valMin or val > self.valMax:
            self.logger.error(_("Wrong value for the progress bar.\n"))
        else:
            perc = (float(val-self.valMin) / (self.valMax - self.valMin)) * 100.
            nb_equals = int(perc * self.length / 100)
            out = '\r %s : %3d %% [%s%s]' % (self.name, perc, nb_equals*'=',
                                             (self.length - nb_equals)*' ' )
            self.logger.info(out)

