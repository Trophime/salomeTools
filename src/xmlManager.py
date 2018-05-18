#!/usr/bin/env python
#-*- coding:utf-8 -*-
#  Copyright (C) 2010-2013  CEA/DEN
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

"""
Utilities to manage write/read xml salometools logging files

| Usage:
| >> import src.xmlManager as XMLMGR
"""

import os
try: # For python2
    import sys
    reload(sys)  
    sys.setdefaultencoding('utf8')
except:
    pass

import src.ElementTree as ETREE
import src.utilsSat as UTS
import dateTime as DATT


##############################################################################
# classes to write and read xml salometools logging files
##############################################################################
class XmlLogFile(object):
    """
    Class to manage writing in salomeTools xml log file
    """
    def __init__(self, filePath, rootname):
        """Initialization
        
        :param filePath: (str) The path to the file where to write the log file
        :param rootname: (str) The name of the root node of the xml file
        :param attrib: (dict) 
          The dictionary that contains the attributes and value of the root node
        """
        self._config = None
        
        # Initialize the filePath and ensure that the directory 
        # that contain the file exists (make it if necessary)
        self.xmlFile = filePath
        
        self.dirXmlFile, baseName = os.path.split(filePath)
        prefix, tmp = os.path.splitext(baseName)
        self.txtFile = os.path.join(self.dirXmlFile, "OUT", prefix + ".txt")
        self.pyconfFile = os.path.join(self.dirXmlFile, "OUT", prefix + ".pyconf")
        
        UTS.ensure_path_exists(self.dirXmlFile)
        UTS.ensure_path_exists(os.path.join(self.dirXmlFile, "OUT"))
        
        # Initialize the field that contain the xml in memory
        self.xmlroot = ETREE.Element(rootname)
        
    def set_config(self, config):
        """needs do be called at least once"""
        self._config = config
    
    def get_config(self):
        return self._config
    
    def write_tree(self, stylesheet=None, file_path = None):
        """Write the xml tree in the log file path. Add the stylesheet if asked.
        
        :param stylesheet: (str) The basename stylesheet to apply to the xml file
        """
        cfg = self._config # shortcut
        log_file_path = self.xmlFile
        if file_path:
          log_file_path = file_path
          
        try:
          if stylesheet:
            fDef = os.path.join(cfg.VARS.srcDir, "xsl", stylesheet) # original default
            fCur = os.path.join(self.dirXmlFile, stylesheet) # local need
            UTS.ensure_file_exists(fCur, fDef)
            fDef = os.path.join(cfg.VARS.srcDir, "xsl", "LOGO-SAT.png") # original default
            fCur = os.path.join(self.dirXmlFile, "LOGO-SAT.png") # local need
            UTS.ensure_file_exists(fCur, fDef)
        except Exception:
          raise Exception("problem writing stylesheet file: %s" % styCur)
        
        try:
          with open(log_file_path, 'w') as f:
            f.write("<?xml version='1.0' encoding='utf-8'?>\n")
            if stylesheet:
              f.write("<?xml-stylesheet type='text/xsl' href='%s'?>\n" % stylesheet)   
            f.write(ETREE.tostring(self.xmlroot, encoding='utf-8'))       
        except Exception:
          raise Exception("problem writing Xml log file: %s" % log_file_path)
        
    def add_simple_node(self, node_name, text=None, attrib={}):
        """Add a node with some attibutes and text to the root node.
        
        :param node_name: (str) the name of the node to add
        :param text: (str) the text of the node
        :param attrib: (dict)
          The dictionary containing the attribute of the new node
        """
        n = ETREE.Element(node_name, attrib=attrib)
        n.text = text
        self.xmlroot.append(n)
        return n
    
    def append_node_text(self, node_name, text):
        """Append a new text to the node that has node_name as name
        
        :param node_name: (str) The name of the node on which append text
        :param text: (str) The text to append
        """
        # find the corresponding node
        for field in self.xmlroot:
            if field.tag == node_name:
                # append the text
                field.text += text

    def set_node_text(self, node_name, text):
        """Set/overwrite a new text to the node that has node_name as name
        
        :param node_name: (str) The name of the node on which append text
        :param text: (str) The text to append
        """
        # find the corresponding node
        for field in self.xmlroot:
            if field.tag == node_name:
                # append the text
                field.text = text

    def append_node_attrib(self, node_name, attrib):
        """Append a new attributes to the node that has node_name as name
        
        :param node_name: (str) The name of the node on which append text
        :param attrib: (dict) The attrib to append
        """
        self.xmlroot.find(node_name).attrib.update(attrib)
        
    def datehourToXml(self, datehour):
        """
        format for attrib xml from config VARS.datehour
        from '20180516_090830' to '16/05/2018 09h08m30s'
        """
        Y, m, dd, H, M, S = DATT.date_to_datetime(datehour)
        res = "%2s/%2s/%4s %2sh%2sm%2ss" % (dd, m, Y, H, M, S)
        return res
        
    def relPath(self, aFile):
        """get relative path of aFile from self.dirXmlFile"""
        return os.path.relpath(aFile, self.dirXmlFile) 
        
    def put_initial_fields(self, config):
        """
        Put all fields corresponding to the command context (user, time, ...)
        """
        self.set_config(config)
        cfg = self._config # shortcut
        
        # append attrib application to root node
        self.xmlroot.attrib.update({"application" : cfg.VARS.application})
        
        # add node Site
        atts = {
          "command": cfg.VARS.command, # command name
          "satversion": cfg.INTERNAL.sat_version, # version of salomeTools
          "hostname": cfg.VARS.hostname, # machine name
          "OS": cfg.VARS.dist, # Distribution of the machine
          "user" : cfg.VARS.user, # The user that have launched the command
          "beginTime" : self.datehourToXml(cfg.VARS.datehour), #when command was launched
          "application" : cfg.VARS.application, # The application if any
          }
        self.add_simple_node("Site", attrib=atts)
        
        # The initialization of the node Log
        self.add_simple_node("Log", text="Empty trace")
        
        # The system commands logs
        self.add_simple_node("OutLog", text=self.relPath(self.txtFile))
        
        # The initialization of the node Links
        # where to put the links to the other sat commands (micro commands)
        # called by any first main command
        self.add_simple_node("Links")
        
    def put_log_field(self, text):
        """
        fill log field for resume command log
        with level step to critical, but without info? (could be verbose)
        """
        self.set_node_text("Log", text)
        
    def put_links_fields(self, links):
        """
        Put all fields corresponding to the links context (micro commands)
        
        :param log_file_name: (str) The file name of the link.
        :param command_name: (str) The name of the command linked.
        :param command_res: (str) The result of the command linked. "0" or "1"
        :param full_launched_command: (str) The full lanch command ("sat command ...")
        """
        xmlLinks = self.xmlroot.find("Links")
        for li in links:
          log_file_name, cmd_name, cmd_res, full_launched_cmd = li
          atts = {
            "command": cmd_name,
            "passed": cmd_res,
            "launchedCommand" : full_launched_cmd,
            }
          self.add_simple_node(xmlLinks, "link", text=log_file_name, attrib=atts)

    def put_final_fields(self, attribute):
        """
        formerly method end_write.
        Called just after ending command. 
        Put all fields corresponding to the command end context 
        (as current time).
        
        :param attribute: (dict) some attribute to set/append to the node "Site".
        """       
        cfg = self._config # shortcut
        t1 = DATT.DateTime(DATT.fromDateHourConfig(cfg.VARS.datehour)) # begin command time
        t2 = DATT.DateTime("now") # current time as end command time
        # print "t1=%s t2=%s" % (t1, t2)
        dt = DATT.DeltaTime(t1, t2)
        
        # Add the fields end and total time of command
        atts = {
          "endTime": t2.toStrXml(),
          "TotalTime": dt.toStrHms(),
          }
        self.append_node_attrib("Site", attrib=atts)
        
        # set/append the attribute passed to the method
        self.append_node_attrib("Site", attrib=attribute)
  
          
    def dump_config(self, config):
        """Dump the config in a pyconf file in the log directory"""
        # no time for logger as closing phase, 
        # if problem raise error... maybe TOFIX
        with open(self.pyconfFile, 'w') as f:
          config.__save__(f)
    

    def write(self, message, level=None, screenOnly=False):
        """
        function used in the commands 
        to print in the terminal and the log file.
        
        :param message: (str) The message to print.
        :param level: (int) 
          The output level corresponding to the message 0 < level < 6.
        :param screenOnly: (bool) if True, do not write in log file.
        """
        # do not write message starting with \r to log file
        if not message.startswith("\r") and not screenOnly:
            self.xmlFile.append_node_text("Log", 
                                          printcolors.cleancolor(message))

        # get user or option output level
        current_output_verbose_level = self.config.USER.output_verbose_level
        if not ('isatty' in dir(sys.stdout) and sys.stdout.isatty()):
            # clean the message color if the terminal is redirected by user
            # ex: sat compile appli > log.txt
            message = printcolors.cleancolor(message)
        
        # Print message regarding the output level value
        if level:
            if level <= current_output_verbose_level and not self.silentSysStd:
                sys.stdout.write(message)
        else:
            if self.default_level <= current_output_verbose_level and not self.silentSysStd:
                sys.stdout.write(message)
        self.flush()

    def error(self, message):
        """Print an error.
        
        :param message: (str:) The message to print.
        """
        # Print in the log file
        self.xmlFile.append_node_text("traces", _('ERROR:') + message)

        # Print in the terminal and clean colors if the terminal 
        # is redirected by user
        if not ('isatty' in dir(sys.stderr) and sys.stderr.isatty()):
            sys.stderr.write(printcolors.printcError(_('ERROR:') + message))
        else:
            sys.stderr.write(_('ERROR:') + message)

        
          
##############################################################################
class ReadXmlFile(object):
    """
    Class to manage reading of an xml log file
    """
    def __init__(self, filePath):
        """Initialization
        
        :param filePath: (str) The xml file to be read
        """
        self.filePath = filePath
        etree_inst = ETREE.parse(filePath)
        self.xmlroot = etree_inst.parse(filePath)

    def getRootAttrib(self):
        """Get the attibutes of the self.xmlroot
        
        :return: (dict) The attributes of the root node
        """
        return self.xmlroot.attrib
    
    def get_attrib(self, node_name):
        """Get the attibutes of the node node_name in self.xmlroot
        
        :param node_name: (str) the name of the node
        :return: (dict) the attibutes of the node node_name in self.xmlroot
        """
        attrib = self.xmlroot.find(node_name).attrib
        # To be python 3 compatible, convert bytes to str if there are any
        fixedAttrib = {}
        for k in attrib.keys():
            if isinstance(k, bytes):
                key = k.decode()
            else:
                key = k
            if isinstance(attrib[k], bytes):
                value = attrib[k].decode()
            else:
                value = attrib[k]
            fixedAttrib[key] = value
        return fixedAttrib
    
    def get_node_text(self, node):
        """
        Get the text of the first node that has name 
        that corresponds to the parameter node
        
        :param node: (str) the name of the node from which get the text
        :return: (str) 
          The text of the first node that has name 
          that corresponds to the parameter node
        """
        return self.xmlroot.find(node).text
    
##############################################################################
# utilities method
##############################################################################
def add_simple_node(root_node, node_name, text=None, attrib={}):
    """Add a node with some attibutes and text to the root node.

    :param root_node: (ETREE.Element) 
      the Etree element where to add the new node    
    :param node_name: (str) the name of the node to add
    :param text: (str) the text of the node
    :param attrib: (dict) 
      the dictionary containing the attribute(s) of the new node
    """
    n = ETREE.Element(node_name, attrib=attrib)
    n.text = text
    root_node.append(n)
    return n

def append_node_attrib(root_node, attrib):
    """Append a new attributes to the node that has node_name as name
    
    :param root_node: (ETREE.Element)
      the Etree element where to append the new attibutes
    :param attrib: (dict) The attrib to append
    """
    root_node.attrib.update(attrib)

def find_node_by_attrib(xmlroot, name_node, key, value):
    """
    Find the first node from xmlroot that has name name_node 
    and that has in its attributes {key : value}. 
    Return the node
    
    :param xmlroot: (ETREE.Element) 
      the Etree element where to search
    :param name_node: (str) the name of node to search
    :param key: (str) the key to search
    :param value: (str) the value to search
    :return: (ETREE.Element) the found node
    """
    l_nodes =  xmlroot.findall(name_node)
    for node in l_nodes:
        if key not in node.attrib.keys():
            continue
        if node.attrib[key] == value:
            return node
    return None
    
def write_report(filename, xmlroot, stylesheet):
    """Writes a report file from a XML tree.
    
    :param filename: (str) The path to the file to create
    :param xmlroot: (ETREE.Element) the Etree element to write to the file
    :param stylesheet: (str) The stylesheet to add to the begin of the file
    """
    if not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))

    with open(filename, "w") as f:
      f.write("<?xml version='1.0' encoding='utf-8'?>\n")
      if len(stylesheet) > 0:
          f.write("<?xml-stylesheet type='text/xsl' href='%s'?>\n" % stylesheet)
      f.write(ETREE.tostring(xmlroot, encoding='utf-8'))
  
    
