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
import re
import glob
import datetime
import stat

import src.debug as DBG
import src.returnCode as RCO
import src.utilsSat as UTS
import src.xmlManager as XMLMGR
import src.system as SYSS
from src.salomeTools import _BaseCommand

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
  """\
  The log command gives access to the logs produced by the salomeTools commands.

  examples:
    >> sat log
  """
  
  name = "log"
  
  def getParser(self):
    """Define all options for command 'sat log <options>'"""
    parser = self.getParserWithHelp()
    parser.add_option(
      't', 'terminal', 'boolean', 'terminal', 
      "Optional: Show sat instances logs, no browser.")
    parser.add_option(
      'l', 'last', 'boolean', 'last', 
      "Show the log of the last launched command.")
    parser.add_option(
      'x', 'last_terminal', 'boolean', 'last_terminal', 
      """Optional: Show compile log of products, no browser.""")
    parser.add_option(
      'f', 'full', 'boolean', 'full', 
      "Optional: Show the logs of ALL the launched commands.")
    parser.add_option(
      'c', 'clean', 'int', 'clean', 
      "Optional: Erase the n most ancient log files.")
    parser.add_option(
      'n', 'no_browser', 'boolean', 'no_browser', 
      "Optional: Do not launch the browser at the end of the command. Only update the hat file.")
    return parser

  def run(self, cmd_arguments):
    """method called for command 'sat log <options>'"""
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
      

    # get the log directory. 
    logDir = UTS.get_log_path(config)
    
    # Print a header
    nb_files_log_dir = len(glob.glob(os.path.join(logDir, "*")))
    info = [("log directory", logDir), 
            ("number of log files", nb_files_log_dir)]
    UTS.logger_info_tuples(logger, info)
    
    # If the clean options is invoked, 
    # do nothing but deleting the concerned files.
    if options.clean:
        nbClean = options.clean
        # get the list of files to remove
        lLogs = UTS.list_log_file(logDir, UTS._log_all_command_file_expression)
        nbLogFiles = len(lLogs)
        # Delete all if the invoked number is bigger than the number of log files
        if nbClean > nbLogFiles:
            nbClean = nbLogFiles
        # Get the list to delete and do the removing
        lLogsToDelete = sorted(lLogs)[:nbClean]
        for filePath, __, __, __, __, __, __ in lLogsToDelete:
            # remove the xml log file
            remove_log_file(filePath, logger)
            # remove also the corresponding txt file in OUT directory
            txtFilePath = os.path.join(os.path.dirname(filePath), 
                            'OUT', 
                            os.path.basename(filePath)[:-len('.xml')] + '.txt')
            remove_log_file(txtFilePath, logger)
            # remove also the corresponding pyconf (do not exist 2016-06) 
            # file in OUT directory
            pyconfFilePath = os.path.join(os.path.dirname(filePath), 
                            'OUT', 
                            os.path.basename(filePath)[:-len('.xml')] + '.pyconf')
            remove_log_file(pyconfFilePath, logger)

        msg = "%i logs deleted" % nbClean
        logger.info("<OK>\n%s\n" % msg)
        return RCO.ReturnCode("OK", msg)

    # determine the commands to show in the hat log
    notShownCommands = list(config.INTERNAL.log.not_shown_commands)
    if options.full:
        notShownCommands = []

    # Find the stylesheets Directory and files
    xslDir = os.path.join(config.VARS.srcDir, 'xsl')
    xslCommand = os.path.join(xslDir, "command.xsl")
    xslHat = os.path.join(xslDir, "hat.xsl")
    xsltest = os.path.join(xslDir, "test.xsl")
    imgLogo = os.path.join(xslDir, "LOGO-SAT.png")
    
    # copy the stylesheets in the log directory
    # OP We use copy instead of copy2 to update the creation date
    #    So we can clean the LOGS directories easily
    shutil.copy(xslCommand, logDir)
    shutil.copy(xslHat, logDir)
    UTS.ensure_path_exists(os.path.join(logDir, "TEST"))
    shutil.copy(xsltest, os.path.join(logDir, "TEST"))
    shutil.copy(imgLogo, logDir)

    # If the last option is invoked, just, show the last log file
    if options.last_terminal:
        src.check_config_has_application(config)
        rootLogDir = os.path.join(config.APPLICATION.workdir, 'LOGS')
        UTS.ensure_path_exists(rootLogDir)
        log_dirs = os.listdir(rootLogDir)
        if log_dirs == []:
          raise Exception("log directory empty")
        log_dirs= sorted(log_dirs)
        res = show_last_logs(logger, config, log_dirs)
        return res

    # If the last option is invoked, just, show the last log file
    if options.last:
        lastLogFilePath = get_last_log_file(
            logDir, notShownCommands + ["config"])
        if lastLogFilePath is None:
            raise Exception("last log file not found in '%s'" % logDir)
        if options.terminal:
            # Show the log corresponding to the selected command call
            res = print_log_command_in_terminal(lastLogFilePath, logger)
        else:
            # open the log xml file in the user editor
            res = SYSS.show_in_editor(config.USER.browser, 
                                      lastLogFilePath, logger)
        return res

    # If the user asks for a terminal display
    if options.terminal:
        # Parse the log directory in order to find 
        # all the files corresponding to the commands
        lLogs = UTS.list_log_file(logDir, UTS._log_macro_command_file_expression)
        lLogsFiltered = []
        for filePath, __, date, __, hour, cmd, __ in lLogs:
            showLog = UTS.show_command_log(filePath, cmd, config.VARS.application, notShownCommands)
            # showLog, cmdAppli, __ = UTS.show_command_log(filePath, cmd, 
            #                     config.VARS.application, notShownCommands)
            cmdAppli = showLog.getValue()[0]
            if showLog.isOk():
                lLogsFiltered.append((filePath, date, hour, cmd, cmdAppli))
            
        lLogsFiltered = sorted(lLogsFiltered)
        nb_logs = len(lLogsFiltered)
        index = 0
        # loop on all files and print it with date, time and command name 
        for __, date, hour, cmd, cmdAppli in lLogsFiltered:          
            num = UTS.label("%2d" % (nb_logs - index))
            logger.info("%s: %13s %s %s %s\n" % (num, cmd, date, hour, cmdAppli))
            index += 1
        
        # ask the user what for what command he wants to be displayed
        x = -1
        while (x < 0):
            x = ask_value(nb_logs)
            if x > 0:
                index = len(lLogsFiltered) - int(x)
                # Show the log corresponding to the selected command call
                print_log_command_in_terminal(lLogsFiltered[index][0], logger)                
                x = 0
        
        return RCO.ReturnCode("OK", "end from user")
                    
    # Create or update the hat xml that gives access to all the commands log files
    logger.info(_("Generating the hat log file (can be long) ... "))
    xmlHatFilePath = os.path.join(logDir, 'hat.xml')
    src.logger.update_hat_xml(logDir, 
                              application = config.VARS.application, 
                              notShownCommands = notShownCommands)
    logger.info("<OK>\n")
    
    # open the hat xml in the user editor
    if not options.no_browser:
        logger.info(_("\nOpening the log file\n"))
        res =  SYSS.show_in_editor(config.USER.browser, xmlHatFilePath, logger)
        return res
    
    return RCO.ReturnCode("OK", "option no browser")
 
def get_last_log_file(logDir, notShownCommands):
    """\
    Used in case of last option. 
    Get the last log command file path.
    
    :param logDir str: The directory where to search the log files
    :param notShownCommands list: the list of commands to ignore
    :return: the path to the last log file
    :rtype: str
    """
    last = (_, 0)
    for fileName in os.listdir(logDir):
        # YYYYMMDD_HHMMSS_namecmd.xml
        sExpr = UTS._log_macro_command_file_expression
        oExpr = re.compile(sExpr)
        if oExpr.search(fileName):
            # get date and hour and format it
            date_hour_cmd = fileName.split('_')
            datehour = date_hour_cmd[0] + date_hour_cmd[1]
            cmd = date_hour_cmd[2]
            if cmd in notShownCommands:
                continue
            if int(datehour) > last[1]:
                last = (fileName, int(datehour))
    if last[1] != 0:
      res = os.path.join(logDir, last[0])
    else:
      res = None #no log file
    return res

def remove_log_file(filePath, logger):
    '''if it exists, print a warning and remove the input file
    
    :param filePath: the path of the file to delete
    :param logger Logger: the logger instance to use for the print 
    '''
    if os.path.exists(filePath):
        logger.debug(UTS.red("Removing %s\n" % filePath))
        os.remove(filePath)

def print_log_command_in_terminal(filePath, logger):
    '''Print the contain of filePath. It contains a command log in xml format.
    
    :param filePath: The command xml file from which extract the commands 
                     context and traces
    :param logger Logger: the logging instance to use in order to print.  
    '''
    logger.debug(_("Reading %s\n") % filePath)
    # Instantiate the ReadXmlFile class that reads xml files
    xmlRead = XMLMGR.ReadXmlFile(filePath)
    # Get the attributes containing the context (user, OS, time, etc..)
    dAttrText = xmlRead.get_attrib('Site')
    # format dAttrText and print the context
    lAttrText = []
    for attrib in dAttrText:
        lAttrText.append((attrib, dAttrText[attrib]))
    
    UTS.logger_info_tuples(logger, lAttrText)
    # Get the traces
    command_traces = xmlRead.get_node_text('Log')
    # Print it if there is any
    if command_traces:
      msg = _("Here are the command traces :\n%s\n") % command_traces
      logger.info(msg)
        
def getMaxFormat(aListOfStr, offset=1):
    """returns format for columns width as '%-30s"' for example"""
    maxLen = max([len(i) for i in aListOfStr]) + offset
    fmt =  "%-" + str(maxLen) + "s" # "%-30s" for example  
    return fmt, maxLen

def show_last_logs(logger, config, log_dirs):
    """Show last compilation logs"""
    log_dir = os.path.join(config.APPLICATION.workdir, 'LOGS')
    # list the logs
    nb = len(log_dirs)
    fmt1, maxLen = getMaxFormat(log_dirs, offset=1)
    fmt2 = "%s: " + fmt1 + "\n"  # "%s: %-30s\n" for example
    nb_cols = 5
    # line ~ no more 100 chars
    if maxLen > 20: nb_cols = 4
    if maxLen > 25: nb_cols = 3
    if maxLen > 33: nb_cols = 2
    if maxLen > 50: nb_cols = 1
    col_size = (nb / nb_cols) + 1
    for index in range(0, col_size):
        msg = ""
        for i in range(0, nb_cols):
            k = index + i * col_size
            if k < nb:
                l = log_dirs[k]
                str_indice = UTS.label("%2d" % (k+1))
                log_name = l
                msg += fmt2 % (str_indice, log_name)
        logger.info(msg + "\n")

    # loop till exit
    x = -1
    while (x < 0):
        x = ask_value(nb)
        if x > 0:
            product_log_dir = os.path.join(log_dir, log_dirs[x-1])
            show_product_last_logs(logger, config, product_log_dir)

def show_product_last_logs(logger, config, product_log_dir):
    """Show last compilation logs of a product"""
    # sort the files chronologically
    l_time_file = []
    for file_n in os.listdir(product_log_dir):
        my_stat = os.stat(os.path.join(product_log_dir, file_n))
        l_time_file.append(
              (datetime.datetime.fromtimestamp(my_stat[stat.ST_MTIME]), file_n))
    
    # display the available logs
    for i, (__, file_name) in enumerate(sorted(l_time_file)):
        str_indice = UTS.label("%2d" % (i+1))
        opt = []
        my_stat = os.stat(os.path.join(product_log_dir, file_name))
        opt.append(str(datetime.datetime.fromtimestamp(my_stat[stat.ST_MTIME])))
        
        opt.append("(%8.2f)" % (my_stat[stat.ST_SIZE] / 1024.0))
        logger.info(" %-35s" % " ".join(opt))
        logger.info("%s: %-30s\n" % (str_indice, file_name))
        
    # loop till exit
    x = -1
    while (x < 0):
        x = ask_value(len(l_time_file))
        if x > 0:
            (__, file_name) =  sorted(l_time_file)[x-1]
            log_file_path = os.path.join(product_log_dir, file_name)
            SYSS.show_in_editor(config.USER.editor, log_file_path, logger)
        
def ask_value(nb):
    '''Ask for an int n. 0<n<nb
    
    :param nb int: The maximum value of the value to be returned by the user.
    :return: the value entered by the user. Return -1 if it is not as expected
    :rtype: int
    '''
    try:
        # ask for a value
        rep = input(_("Which one (enter or 0 to quit)? "))
        # Verify it is on the right range
        if len(rep) == 0:
            x = 0
        else:
            x = int(rep)
            if x > nb:
                x = -1
    except:
        x = -1
    
    return x
