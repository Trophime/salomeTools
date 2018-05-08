#!/usr/bin/env python
#-*- coding:utf-8 -*-

#  Copyright (C) 2010-2018  CEA/DEN
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
import unittest

import initializeTest # set PATH etc for test

import src.salomeTools as SAT
import src.debug as DBG # Easy print stderr (for DEBUG only)
import src.loggingSat as LOG

class TestCase(unittest.TestCase):
  "Test the sat commands on APPLI_TEST configuration pyconf etc. files"""
  
  logger = LOG.getUnittestLogger()
  debug = False
  
  #see test_100, # commands are expected OK
  TRG = "SALOME-8.4.0"
  satCommandsToTestOk = [
    "config -l",
    "config -v .",
    "config -d .",
    "config %s --value ." %  TRG,
    "config %s --debug ." %  TRG,
    "config %s --info KERNEL" %  TRG,
    "config %s --show_patchs" %  TRG,
  ]
  #see test_110, # commands are expected KO
  satCommandsToTestKo = [
    "config %s --info oops" %  TRG,
  ]
  #see test_120, # commands are expected KO
  satCommandsToTestRaise = [
    "oopsconfig --oops .",
    "config --oops",
  ]
  
  def tearDown(self):
    # print "tearDown", __file__
    # assure self.logger clear for next test
    logs = self.logger.getLogsAndClear()
    # using assertNotIn() is too much verbose
    self.assertFalse("ERROR    ::" in logs)
    self.assertFalse("CRITICAL ::" in logs)

  def test_000(self):
    # one shot setUp() for this TestCase
    if self.debug: DBG.push_debug(True)
    SAT.setNotLocale() # test english
    return

  def test_999(self):
    # one shot tearDown() for this TestCase
    SAT.setLocale() # end test english
    if self.debug: DBG.pop_debug()

  def test_010(self):
    cmd = "config -l"
    s = SAT.Sat(self.logger)
    DBG.write("s.getConfig()", s.getConfig()) #none
    DBG.write("s.__dict__", s.__dict__) # have 
    returnCode = s.execute_cli(cmd)
    DBG.write("test_010 returnCode", returnCode)
    logs = self.logger.getLogs()
    DBG.write("test_010 logger", logs)
    self.assertTrue(returnCode.isOk())
    
  def test_100(self):
    # test all satCommands expected OK
    dbg = self.debug # True # 
    for cmd in self.satCommandsToTestOk:
      s = SAT.Sat(self.logger)
      returnCode = s.execute_cli(cmd)
      DBG.write("test_800 'sat %s' returnCode" % cmd, str(returnCode), True)
      logs = self.logger.getLogsAndClear()
      DBG.write("logs", logs, dbg)    
      # using assertNotIn() is too much verbose
      self.assertFalse("ERROR    ::" in logs)
      self.assertFalse("CRITICAL ::" in logs)
      
  def test_110(self):
    # test all satCommands expected KO
    dbg = self.debug
    for cmd in self.satCommandsToTestKo:
      s = SAT.Sat(self.logger)
      returnCode = s.execute_cli(cmd)
      DBG.write("test_810 'sat %s' returnCode" % cmd, returnCode, dbg)
      logs = self.logger.getLogsAndClear()
      DBG.write("logs", logs, dbg)    
      
  def test_120(self):
    # test all satCommands expected raise
    dbg = self.debug
    for cmd in self.satCommandsToTestRaise:
      s = SAT.Sat(self.logger)
      DBG.write("test_820 'sat %s'" % cmd, "expected raise", dbg)
      with self.assertRaises(Exception):
        returnCode = s.execute_cli(cmd)
      logs = self.logger.getLogsAndClear()
      DBG.write("logs", logs, dbg)    
      
      
if __name__ == '__main__':
    unittest.main(exit=False)
    pass
