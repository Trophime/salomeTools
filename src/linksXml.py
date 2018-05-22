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
Contains LinkXml class to store logger tree structure of 
main command calls sequence of microcommand(s) 
which calls other sequence of microcommand(s) etc.
command(s) are identified (and their logger handler(s)) 
by '_idCommandHandlers' attribute
"""

import pprint as PP
      
class LinkXml(object):
  """
  class to store logger tree structure of 
  main command calls sequence of microcommand(s) 
  which calls other sequence of microcommand(s) etc.
  Before and during and after execution of theses commands
  permits storing information(s) for final writing file(s) logs xml
  """
  # authorized attributes for setAttribLinksForCommand()
  _authAttrib = "log_file_name cmd_name cmd_res full_launched_cmd".split(" ")
  
  def __init__(self, idName):
    """Initialization
        
    :param idName: (int) The id as idCmdHandler
      for original/root node is set to -1
    """
    self.reset(idName)

  def reset(self, idName=None):
    # after execution of command info to set (as cmd result)
    self.idName = idName 
    self.log_file_name = None
    self.cmd_name = None
    self.cmd_res = None
    self.full_launched_cmd = None
    # future could add more informations attributes here...
    self._linksXml = []  # empty list of linkXml for micro commands
            
  def __repr__(self):
    aDict = {
      "idName": self.idName,
      "log_file_name": self.log_file_name,
      "full_launched_cmd": self.full_launched_cmd,
      "self.cmd_res": self.cmd_res,
      "links": self._linksXml,
    }
    tmp = PP.pformat(aDict)
    res = "LinkXml(%s)" % tmp[1:-1]
    return res
      
  def findLink(self, idName):
    if self.idName == idName:
      return self
    else:
      for i in self._linksXml:
        res = i.findLink(idName)
        if res is not None: 
          return res
    return None
    
  def appendLink(self, idName):
    import src.debug as DBG
    if self.findLink(idName) is not None:
      msg = "appendLink: idname '%s' existing yet" % idName
      DBG.write(msg, self, True)
      raise Exception(msg)
    app = LinkXml(idName)
    self._linksXml.append(app)
    return app
    
  def getAllIdNames(self):
    """recursive trip for sequence xml"""
    res = [self.idName]
    for i in self._linksXml:
      res.extend(i.getAllIdNames())
    return res
    
  def setAuthAttr(self, nameAttrib, value):
    if nameAttrib in self._authAttrib:
      self.__setattr__(nameAttrib, value) # without precaution
    else:
      msg = "setAuthAttr %s attribute not authorized" % nameAttrib
      raise Exception(msg)
    

#####################################################
# module methods and singleton
#####################################################    

_LinkXml = LinkXml(-1) # singleton instance root -1

def getLinksXml():
  """get singleton instance for everywhere easy access"""
  return _LinkXml

def resetLinksXml():
  """reset singleton instance for everywhere easy access"""
  _LinkXml.reset(-1) # singleton instance root -1
  
def appendLinkForCommand(cmdParent, cmdNew):
  """init a new link for a new command in singleton tree"""
  k0 = getLinksXml() # get singleton
  idParent = cmdParent.getId()
  idNew = cmdNew.getId()
  kParent = k0.findLink(idParent)
  if kParent is None:
    msg = "cmdParent id %i not found" % idParent
    raise Exception(msg)
  import src.debug as DBG
  kNew = kParent.appendLink(idNew)
  DBG.write("appendLinkForCommand %i for parent %i" % (idNew, idParent), k0, True)  
  return kNew
  
def setAttribLinkForCommand(cmd, nameAttrib, value):
  """init an attribute value in link of a command in singleton tree"""
  k0 = getLinksXml() # get singleton
  idCmd = cmd.getId()
  kCmd = k0.findLink(idCmd)
  k0.setAuthAttr(nameAttrib, value)
  

