#!/usr/bin/env python
#-*- coding:utf-8 -*-

#  Copyright (C) 2018-20xx  CEA/DEN
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
This file contains ReturnCode class
usage:
>> import returnCode as RCO
"""

import os
import sys
 
# OKSYS and KOSYS seems equal on linux or windows
OKSYS = 0  # OK 
KOSYS = 1  # KO
OK_STATUS = "OK"
KO_STATUS = "KO"

#####################################################
class ReturnCode(object):

  """
  assume simple return code for methods, with explanation as 'why'
  obviously why it is not OK, but also why it is OK (if you want)
  usage:
  >> import returnCode as RCO
  >> return RCO.ReturnCode("KO", "there is no problem here")
  >> return RCO.ReturnCode("KO", "there is a problem here because etc")
  >> return RCO.ReturnCode("TIMEOUT_STATUS", "too long here because etc")
  >> return RCO.ReturnCode("NA", "not applicable here because etc")
  """

  OK_STATUS = "OK"
  KO_STATUS = "KO"
  NA_STATUS = "NA" # not applicable
  UNKNOWN_STATUS = "ND" # not defined
  KNOWNFAILURE_STATUS = "KF"
  TIMEOUT_STATUS = "TIMEOUT"

  # integer for sys.exit(anInt)
  # OKSYS and KOSYS seems equal on linux or windows
  OKSYS = 0  # OK 
  KOSYS = 1  # KO
  NASYS = 2  # KO not applicable return code
  NDSYS = 3  # KO not defined return code
  KFSYS = 4  # KO known failure return code
  TOSYS = 5  # KO time out
  
  _TOSYS = { 
    OK_STATUS: OKSYS,
    KO_STATUS: KOSYS,
    NA_STATUS: NASYS,
    UNKNOWN_STATUS: NDSYS,
    KNOWNFAILURE_STATUS: KFSYS,
    TIMEOUT_STATUS: TOSYS, 
  }
  _DEFAULT_WHY = "No given explanation"

  def __init__(self, status=None, why=None):
    if status is None:
      aStatus = self.UNKNOWN_STATUS
      self._why = self._DEFAULT_WHY  
    else:
      self.setStatus(status, why)
    
  def __repr__(self):
    res = "%s: '%s'" % (self._status, self.indent(self._why))
    return res

  def indent(self, text, amount=5, ch=' '):
      """indent multi lines message"""
      padding = amount * ch
      res = ''.join(padding + line for line in text.splitlines(True))
      return res[amount:]

  def __add__(self, value):
    """allows expression 'returnCode1 + returnCode2 + ...' """
    isOk = self.isOk() and value.isOk()
    if isOk: 
      return ReturnCode("OK", "%s\n%s" % (self.getWhy(), value.getWhy()) )
    else:
      return ReturnCode("KO", "%s\n%s" % (self.getWhy(), value.getWhy()) )
  
  def toSys(self):
    try:
      return self._TOSYS[self._status]
    except:
      return self._TOSYS[self.NA_STATUS]
    
  def getWhy(self):
    return self._why
    
  def getWhy(self):
    return self._why
    
  def setWhy(self, why):
    self._why = why
    
  def setStatus(self, status, why=None):
    if why is None: 
      aWhy = self._DEFAULT_WHY
    else:
      aWhy = why
    if status in self._TOSYS.keys():
      self._status = status
      self._why = aWhy
    else:
      self._status = self.NA_STATUS
      self._why = "Error status '%s' for '%s'" % (status, aWhy)

  def isOk(self):
    return (self._status == self.OK_STATUS)



