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
import sys
import shutil
import subprocess
import gzip

import src.debug as DBG
import src.returnCode as RCO
import src.utilsSat as UTS
from src.salomeTools import _BaseCommand
import src.ElementTree as ETREE
import src.xmlManager as XMLMGR
import src.architecture as ARCH
import src.test_module as TMOD
import src.dateTime as DATT

try:
    from hashlib import sha1
except ImportError:
    from sha import sha as sha1


########################################################################
# Command class
########################################################################
class Command(_BaseCommand):
  """
  The test command runs a test base on a SALOME installation.
  
  | Examples:
  | >> sat test SALOME --grid GEOM --session light
  """
  
  name = "test"
  
  def getParser(self):
    """Define all options for command 'sat test <options>'"""
    parser = self.getParserWithHelp()
    parser.add_option('b', 'base', 'string', 'base',
        _("""\
Optional: Indicate the name of the test base to use.
  This name has to be registered in your application and in a project.
  A path to a test base can also be used."""))
    parser.add_option('l', 'launcher', 'string', 'launcher',
        _("Optional: Use this option to specify the path to a SALOME launcher to "
          "use to launch the test scripts of the test base."))
    parser.add_option('g', 'grid', 'list', 'grids',
        _('Optional: Indicate which grid(s) to test (subdirectory of the test base).'))
    parser.add_option('s', 'session', 'list', 'sessions',
        _('Optional: indicate which session(s) to test (subdirectory of the grid).'))
    parser.add_option('', 'display', 'string', 'display',
        _("""\
Optional: set the display where to launch SALOME.
  If value is NO then option --show-desktop=0 will be used to launch SALOME."""))
    return parser

  def check_option(self, options):
    """Check the options
    
    :param options: (Options) The options
    :return: None
    """
    if not options.launcher:
        options.launcher = ""
    elif not os.path.isabs(options.launcher):
        returnCode = UTS.check_config_has_application(config)
        if not returnCode.isOk():
            msg = _("An application is required to use a relative path with option --appli")
            raise Exception(msg)
        options.launcher = os.path.join(config.APPLICATION.workdir, options.launcher)
        if not os.path.exists(options.launcher):
            raise Exception(_("Launcher %s not found") % options.launcher )
    return

  def run(self, cmd_arguments):
    """method called for command 'sat test <options>'"""
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

    self.check_option(options)

    # the test base is specified either by the application, or by the --base option
    with_application = False
    if config.VARS.application != 'None':
        logger.info(_('Running tests on application %s\n') % 
                     UTS.label(config.VARS.application))
        with_application = True
    elif not options.base:
        raise Exception(
          _('A test base is required. Use the --base option') )

    # the launcher is specified either by the application, or by the --launcher option
    if with_application:
        # check if environment is loaded
        if 'KERNEL_ROOT_DIR' in os.environ:
            logger.warning(_("SALOME environment already sourced"))
              
    elif options.launcher:
        logger.info(_("Running SALOME application."))
    else:
        msg = _("""\
Impossible to find any launcher.
Please specify an application or a launcher
""")
        logger.error(msg)
        return 1

    # set the display
    show_desktop = (options.display and options.display.upper() == "NO")
    if options.display and options.display != "NO":
        remote_name = options.display.split(':')[0]
        if remote_name != "":
            check_remote_machine(remote_name, logger)
        # if explicitly set use user choice
        os.environ['DISPLAY'] = options.display
    elif 'DISPLAY' not in os.environ:
        # if no display set
        if ('test' in config.LOCAL and
                'display' in config.LOCAL.test and 
                len(config.LOCAL.test.display) > 0):
            # use default value for test tool
            os.environ['DISPLAY'] = config.LOCAL.test.display
        else:
            os.environ['DISPLAY'] = "localhost:0.0"

    # initialization
    #################
    if with_application:
        tmp_dir = os.path.join(config.VARS.tmp_root,
                               config.APPLICATION.name,
                               "test")
    else:
        tmp_dir = os.path.join(config.VARS.tmp_root,
                               "test")

    # remove previous tmp dir
    if os.access(tmp_dir, os.F_OK):
        try:
            shutil.rmtree(tmp_dir)
        except:
            logger.error(
                _("error removing TT_TMP_RESULT %s\n") % tmp_dir)

    lines = []
    lines.append("date = '%s'" % config.VARS.date)
    lines.append("hour = '%s'" % config.VARS.hour)
    lines.append("node = '%s'" % config.VARS.node)
    lines.append("arch = '%s'" % config.VARS.dist)

    if 'APPLICATION' in config:
        lines.append("application_info = {}")
        lines.append("application_info['name'] = '%s'" % 
                     config.APPLICATION.name)
        lines.append("application_info['tag'] = '%s'" % 
                     config.APPLICATION.tag)
        lines.append("application_info['products'] = %s" % 
                     str(config.APPLICATION.products))

    content = "\n".join(lines)

    # create hash from context information
    dirname = sha1(content.encode()).hexdigest()
    base_dir = os.path.join(tmp_dir, dirname)
    os.makedirs(base_dir)
    os.environ['TT_TMP_RESULT'] = base_dir

    # create env_info file
    f = open(os.path.join(base_dir, 'env_info.py'), "w")
    f.write(content)
    f.close()

    # create working dir and bases dir
    working_dir = os.path.join(base_dir, 'WORK')
    os.makedirs(working_dir)
    os.makedirs(os.path.join(base_dir, 'BASES'))
    os.chdir(working_dir)

    if 'PYTHONPATH' not in os.environ:
        os.environ['PYTHONPATH'] = ''
    else:
        for var in os.environ['PYTHONPATH'].split(':'):
            if var not in sys.path:
                sys.path.append(var)

    # launch of the tests
    #####################
    test_base = ""
    if options.base:
        test_base = options.base
    elif with_application and "test_base" in config.APPLICATION:
        test_base = config.APPLICATION.test_base.name

    fmt = "  %s = %s\n"
    msg  = fmt % (_('Display'), os.environ['DISPLAY'])
    msg += fmt % (_('Timeout'), TMOD.DEFAULT_TIMEOUT)
    msg += fmt % (_("Working dir"), base_dir)
    logger.info(msg)

    # create the test object
    test_runner = TMOD.Test(config,
                            logger,
                            base_dir,
                            testbase=test_base,
                            grids=options.grids,
                            sessions=options.sessions,
                            launcher=options.launcher,
                            show_desktop=show_desktop)
    
    if not test_runner.test_base_found:
        # Fail 
        return 1
        
    # run the test
    logger.allowPrintLevel = False
    retcode = test_runner.run_all_tests()
    logger.allowPrintLevel = True

    logger.info(_("Tests finished\n"))
    
    logger.debug(_("Generate the specific test log\n"))
    log_dir = UTS.get_log_path(config)
    out_dir = os.path.join(log_dir, "TEST")
    UTS.ensure_path_exists(out_dir)
    name_xml_board = logger.logFileName.split(".")[0] + "board" + ".xml"
    historic_xml_path = generate_history_xml_path(config, test_base)
    
    create_test_report(config,
                       historic_xml_path,
                       out_dir,
                       retcode,
                       xmlname = name_xml_board)
    xml_board_path = os.path.join(out_dir, name_xml_board)

    logger.l_logFiles.append(xml_board_path)
    logger.add_link(os.path.join("TEST", name_xml_board),
                    "board",
                    retcode,
                    "Click on the link to get the detailed test results")
    
    # Add the historic files into the log files list of the command
    logger.l_logFiles.append(historic_xml_path)
    
    logger.debug(_("Removing the temporary directory: %s") % test_runner.tmp_working_dir)
    if os.path.exists(test_runner.tmp_working_dir):
        shutil.rmtree(test_runner.tmp_working_dir)

    return retcode
   

def ask_a_path():
    """
    interactive as using 'raw_input'
    """
    path = raw_input("enter a path where to save the result: ")
    if path == "":
        result = raw_input("the result will be not save. Are you sure to "
                           "continue ? [y/n] ")
        if result == "y":
            return path
        else:
            return ask_a_path()

    elif os.path.exists(path):
        result = raw_input("WARNING: the content of %s will be deleted. Are you"
                           " sure to continue ? [y/n] " % path)
        if result == "y":
            return path
        else:
            return ask_a_path()
    else:
        return path

def save_file(filename, base):
    f = open(filename, 'r')
    content = f.read()
    f.close()

    objectname = sha1(content).hexdigest()

    f = gzip.open(os.path.join(base, '.objects', objectname), 'w')
    f.write(content)
    f.close()
    return objectname

def move_test_results(in_dir, what, out_dir, logger):
    if out_dir == in_dir:
        return

    finalPath = out_dir
    pathIsOk = False
    while not pathIsOk:
        try:
            # create test results directory if necessary
            #logger.debug("FINAL = %s\n" % finalPath)
            if not os.access(finalPath, os.F_OK):
                #shutil.rmtree(finalPath)
                os.makedirs(finalPath)
            pathIsOk = True
        except:
            logger.error(_("%s cannot be created.") % finalPath)
            finalPath = ask_a_path()

    if finalPath != "":
        os.makedirs(os.path.join(finalPath, what, 'BASES'))

        # check if .objects directory exists
        if not os.access(os.path.join(finalPath, '.objects'), os.F_OK):
            os.makedirs(os.path.join(finalPath, '.objects'))

        logger.info(_('copy tests results to %s ... ') % finalPath)

        # copy env_info.py
        shutil.copy2(os.path.join(in_dir, what, 'env_info.py'),
                     os.path.join(finalPath, what, 'env_info.py'))

        # for all sub directory (ie testbase) in the BASES directory
        for testbase in os.listdir(os.path.join(in_dir, what, 'BASES')):
            outtestbase = os.path.join(finalPath, what, 'BASES', testbase)
            intestbase = os.path.join(in_dir, what, 'BASES', testbase)

            # ignore files in root dir
            if not os.path.isdir(intestbase):
                continue

            os.makedirs(outtestbase)
            #logger.debug("copy testbase %s\n" % testbase)

            for grid_ in [m for m in os.listdir(intestbase) if os.path.isdir(
                                                os.path.join(intestbase, m))]:
                # ignore source configuration directories
                if grid_[:4] == '.git' or grid_ == 'CVS':
                    continue

                outgrid = os.path.join(outtestbase, grid_)
                ingrid = os.path.join(intestbase, grid_)
                os.makedirs(outgrid)
                #logger.debug("copy grid %s" % grid_)

                if grid_ == 'RESSOURCES':
                    for file_name in os.listdir(ingrid):
                        if not os.path.isfile(os.path.join(ingrid,
                                                           file_name)):
                            continue
                        f = open(os.path.join(outgrid, file_name), "w")
                        f.write(save_file(os.path.join(ingrid, file_name),
                                          finalPath))
                        f.close()
                else:
                    for session_name in [t for t in os.listdir(ingrid) if 
                                      os.path.isdir(os.path.join(ingrid, t))]:
                        outsession = os.path.join(outgrid, session_name)
                        insession = os.path.join(ingrid, session_name)
                        os.makedirs(outsession)
                        
                        for file_name in os.listdir(insession):
                            if not os.path.isfile(os.path.join(insession,
                                                               file_name)):
                                continue
                            if file_name.endswith('result.py'):
                                shutil.copy2(os.path.join(insession, file_name),
                                             os.path.join(outsession, file_name))
                            else:
                                f = open(os.path.join(outsession, file_name), "w")
                                f.write(save_file(os.path.join(insession,
                                                               file_name),
                                                  finalPath))
                                f.close()

    logger.info("<OK>\n")

def check_remote_machine(machine_name, logger):
    logger.debug(_("Check the display on %s\n") % machine_name)
    ssh_cmd = """
set -x
ssh -o "StrictHostKeyChecking no" %s "whoami"
""" % machine_name
    res = UTS.Popen(ssh_cmd, shell=True, logger=logger)

def create_test_report(config,
                       xml_history_path,
                       dest_path,
                       retcode,
                       xmlname=""):
    """
    Creates the XML report for a product.
    """
    ASNODE = XMLMGR.add_simple_node # shortcut
    ETELEM = ETREE.Element # shortcut

    # get the date and hour of the launching of the command, in order to keep
    # history
    date_hour = config.VARS.datehour
    
    # Get some information to put in the xml file
    application_name = config.VARS.application
    withappli = UTS.check_config_has_application(config).isOk()
    
    first_time = False
    if not os.path.exists(xml_history_path):
        first_time = True
        root = ETELEM("salome")
        prod_node = ETELEM("product", name=application_name, build=xmlname)
        root.append(prod_node)
    else:
        root = ETREE.parse(xml_history_path).getroot()
        prod_node = root.find("product")
    
    prod_node.attrib["history_file"] = os.path.basename(xml_history_path)
    prod_node.attrib["global_res"] = retcode
    
    if withappli:
        if not first_time:
            for node in (prod_node.findall("version_to_download") + 
                         prod_node.findall("out_dir")):
                prod_node.remove(node)
                
        ASNODE(prod_node, "version_to_download", config.APPLICATION.name)
        ASNODE(prod_node, "out_dir", config.APPLICATION.workdir)

    # add environment
    if not first_time:
        for node in prod_node.findall("exec"):
                prod_node.remove(node)
        
    exec_node = ASNODE(prod_node, "exec")
    exec_node.append(ETELEM("env", name="Host", value=config.VARS.node))
    exec_node.append(ETELEM("env", name="Architecture", value=config.VARS.dist))
    exec_node.append(ETELEM("env", name="Number of processors", value=str(config.VARS.nb_proc)))    
    exec_node.append(ETELEM("env", name="Begin date", value=UTS.parse_date(date_hour)))
    exec_node.append(ETELEM("env", name="Command", value=config.VARS.command))
    exec_node.append(ETELEM("env", name="sat version", value=config.INTERNAL.sat_version))

    if 'TESTS' in config:
        if first_time:
            tests = ASNODE(prod_node, "tests")
            known_errors = ASNODE(prod_node, "known_errors")
            new_errors = ASNODE(prod_node, "new_errors")
            amend = ASNODE(prod_node, "amend")
        else:
            tests = prod_node.find("tests")
            known_errors = prod_node.find("known_errors")
            new_errors = prod_node.find("new_errors")
            amend = prod_node.find("amend")
        
        tt = {}
        for test in config.TESTS:
            if not tt.has_key(test.testbase):
                tt[test.testbase] = [test]
            else:
                tt[test.testbase].append(test)
        
        for testbase in tt.keys():
            if first_time:
                gn = ASNODE(tests, "testbase")
            else:
                gn = tests.find("testbase")
                # initialize all grids and session to "not executed"
                for mn in gn.findall("grid"):
                    mn.attrib["executed_last_time"] = "no"
                    for tyn in mn.findall("session"):
                        tyn.attrib["executed_last_time"] = "no"
                        for test_node in tyn.findall('test'):
                            for node in test_node.getchildren():
                                if node.tag != "history":
                                    test_node.remove(node)
                            
                            attribs_to_pop = []    
                            for attribute in test_node.attrib:
                                if (attribute != "script" and 
                                                        attribute != "res"):
                                    attribs_to_pop.append(attribute)
                            for attribute in attribs_to_pop:
                                test_node.attrib.pop(attribute)
            
            gn.attrib['name'] = testbase
            nb, nb_pass, nb_failed, nb_timeout, nb_not_run = 0, 0, 0, 0, 0
            grids = {}
            sessions = {}
            for test in tt[testbase]:
                if not grids.has_key(test.grid):
                    if first_time:
                        mn = ASNODE(gn, "grid")
                        mn.attrib['name'] = test.grid
                    else:
                        l_mn = gn.findall("grid")
                        mn = None
                        for grid_node in l_mn:
                            if grid_node.attrib['name'] == test.grid:
                                mn = grid_node
                                break
                        if mn == None:
                            mn = ASNODE(gn, "grid")
                            mn.attrib['name'] = test.grid
                    
                    grids[test.grid] = mn
                
                mn.attrib["executed_last_time"] = "yes"
                
                if not sessions.has_key("%s/%s" % (test.grid, test.session)):
                    if first_time:
                        tyn = ASNODE(mn, "session")
                        tyn.attrib['name'] = test.session
                    else:
                        l_tyn = mn.findall("session")
                        tyn = None
                        for session_node in l_tyn:
                            if session_node.attrib['name'] == test.session:
                                tyn = session_node
                                break
                        if tyn == None:
                            tyn = ASNODE(mn, "session")
                            tyn.attrib['name'] = test.session
                        
                    sessions["%s/%s" % (test.grid, test.session)] = tyn

                tyn.attrib["executed_last_time"] = "yes"

                for script in test.script:
                    if first_time:
                        tn = ASNODE(sessions[
                                           "%s/%s" % (test.grid, test.session)],
                                             "test")
                        tn.attrib['session'] = test.session
                        tn.attrib['script'] = script.name
                        hn = ASNODE(tn, "history")
                    else:
                        l_tn = sessions["%s/%s" % (test.grid, test.session)].findall(
                                                                         "test")
                        tn = None
                        for test_node in l_tn:
                            if test_node.attrib['script'] == script['name']:
                                tn = test_node
                                break
                        
                        if tn == None:
                            tn = ASNODE(sessions[
                                           "%s/%s" % (test.grid, test.session)],
                                             "test")
                            tn.attrib['session'] = test.session
                            tn.attrib['script'] = script.name
                            hn = ASNODE(tn, "history")
                        else:
                            # Get or create the history node for the current test
                            if len(tn.findall("history")) == 0:
                                hn = ASNODE(tn, "history")
                            else:
                                hn = tn.find("history")
                            # Put the last test data into the history
                            if 'res' in tn.attrib:
                                attributes = {"date_hour" : date_hour,
                                              "res" : tn.attrib['res'] }
                                ASNODE(hn,
                                                "previous_test",
                                                attrib=attributes)
                            for node in tn:
                                if node.tag != "history":
                                    tn.remove(node)
                    
                    if 'callback' in script:
                        try:
                            cnode = ASNODE(tn, "callback")
                            if ARCH.is_windows():
                                import string
                                cnode.text = filter(
                                                lambda x: x in string.printable,
                                                script.callback)
                            else:
                                cnode.text = script.callback.decode(
                                                                'string_escape')
                        except UnicodeDecodeError as exc:
                            zz = (script.callback[:exc.start] +
                                  '?' +
                                  script.callback[exc.end-2:])
                            cnode = ASNODE(tn, "callback")
                            cnode.text = zz.decode("UTF-8")
                    
                    # Add the script content
                    cnode = ASNODE(tn, "content")
                    cnode.text = script.content
                    
                    # Add the script execution log
                    cnode = ASNODE(tn, "out")
                    cnode.text = script.out
                    
                    if 'amend' in script:
                        cnode = ASNODE(tn, "amend")
                        cnode.text = script.amend.decode("UTF-8")

                    if script.time < 0:
                        tn.attrib['exec_time'] = "?"
                    else:
                        tn.attrib['exec_time'] = "%.3f" % script.time
                    tn.attrib['res'] = script.res

                    if "amend" in script:
                        amend_test = ASNODE(amend, "atest")
                        amend_test.attrib['name'] = os.path.join(test.grid,
                                                                 test.session,
                                                                 script.name)
                        amend_test.attrib['reason'] = script.amend.decode("UTF-8")

                    # calculate status
                    nb += 1
                    if script.res == RCO._OK_STATUS: nb_pass += 1
                    elif script.res == RCO._TIMEOUT_STATUS: nb_timeout += 1
                    elif script.res == RCO._KO_STATUS: nb_failed += 1
                    else: nb_not_run += 1

                    if "known_error" in script:
                        kf_script = ASNODE(known_errors, "error")
                        kf_script.attrib['name'] = os.path.join(test.grid,
                                                                test.session,
                                                                script.name)
                        kf_script.attrib['date'] = script.known_error.date
                        kf_script.attrib['expected'] = script.known_error.expected
                        kf_script.attrib['comment'] = script.known_error.comment.decode("UTF-8")
                        kf_script.attrib['fixed'] = str(script.known_error.fixed)
                        overdue = DATT.DateTime("now").toStrPackage() > script.known_error.expected
                        if overdue:
                            kf_script.attrib['overdue'] = str(overdue)
                        
                    elif script.res == RCO._KO_STATUS:
                        new_err = ASNODE(new_errors, "new_error")
                        script_path = os.path.join(test.grid, test.session, script.name)
                        new_err.attrib['name'] = script_path
                        new_err.attrib['cmd'] = "sat testerror %s -s %s -c 'my comment' -p %s" % \
                            (application_name, script_path, config.VARS.dist)


            gn.attrib['total'] = str(nb)
            gn.attrib['pass'] = str(nb_pass)
            gn.attrib['failed'] = str(nb_failed)
            gn.attrib['timeout'] = str(nb_timeout)
            gn.attrib['not_run'] = str(nb_not_run)
            
            # Remove the res attribute of all tests that were not launched 
            # this time
            for mn in gn.findall("grid"):
                if mn.attrib["executed_last_time"] == "no":
                    for tyn in mn.findall("session"):
                        if tyn.attrib["executed_last_time"] == "no":
                            for test_node in tyn.findall('test'):
                                if "res" in test_node.attrib:
                                    test_node.attrib.pop("res")          
    
    if len(xmlname) == 0:
        xmlname = application_name
    if not xmlname.endswith(".xml"):
        xmlname += ".xml"

    XMLMGR.write_report(os.path.join(dest_path, xmlname), root, "test.xsl")
    XMLMGR.write_report(xml_history_path, root, "test_history.xsl")
    return RCO._OK_STATUS

def generate_history_xml_path(config, test_base):
    """
    Generate the name of the xml file that contain the history of the tests
    on the machine with the current APPLICATION and the current test base.
    
    :param config: (Config) The global configuration
    :param test_base: (str) The test base name (or path)
    :return: (str) the full path of the history xml file
    """
    history_xml_name = ""
    if "APPLICATION" in config:
        history_xml_name += config.APPLICATION.name
        history_xml_name += "-" 
    history_xml_name += config.VARS.dist
    history_xml_name += "-"
    test_base_name = test_base
    if os.path.exists(test_base):
        test_base_name = os.path.basename(test_base)
    history_xml_name += test_base_name
    history_xml_name += ".xml"
    log_dir = UTS.get_log_path(config)
    return os.path.join(log_dir, "TEST", history_xml_name)
