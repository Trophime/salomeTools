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

import src.salomeTools as SAT
import src.debug as DBG # Easy print stderr (for DEBUG only)
import src.loggingSat as LOG

class TestCase(unittest.TestCase):
  "Test the sat --help commands"""
  
  logger = LOG.getUnittestLogger()
  debug = False
  
  def tearDown(self):
    # print "tearDown", __file__
    # assure self.logger clear for next test
    logs = self.logger.getLogsAndClear()
    # using assertNotIn() is too much verbose
    self.assertFalse("ERROR" in logs)
    self.assertFalse("CRITICAL" in logs)
  
  def test_000(self):
    # one shot setUp() for this TestCase
    if self.debug: DBG.push_debug(True)
    SAT.setNotLocale() # test english

  def test_999(self):
    # one shot tearDown() for this TestCase
    SAT.setLocale() # end test english
    if self.debug: DBG.pop_debug()

  def test_010(self):
    cmd = "sat --help"
    stdout, stderr = SAT.launchSat(cmd)
    DBG.write("test_010 stdout", stdout)
    DBG.write("test_010 stderr", stderr)
    self.assertEqual(stderr, "")
    self.assertTrue(" - config" in stdout)
    self.assertTrue(" - prepare" in stdout)
    self.assertTrue(" - compile" in stdout)

  def test_011(self):
    cmd = "--help"
    s = SAT.Sat(self.logger)
    returnCode = s.execute_cli(cmd)
    self.assertTrue(returnCode.isOk())
    logs = self.logger.getLogs()
    DBG.write("test_011 logger", logs)
    self.assertTrue(" - config" in logs)
    self.assertTrue(" - prepare" in logs)
    self.assertTrue(" - compile" in logs)
    
  def test_030(self):
    cmd = "sat config --help"
    stdout, stderr = SAT.launchSat(cmd)
    DBG.write("test_030 stdout", stdout)
    self.assertEqual(stderr, "")
    self.assertTrue("--value" in stdout)

  def test_031(self):
    cmd = "config --help"
    s = SAT.Sat(self.logger)
    returnCode = s.execute_cli(cmd)
    self.assertTrue(returnCode.isOk())
    logs = self.logger.getLogs()
    DBG.write("test_031 logger", logs)
    self.assertTrue("--value" in logs)
    
  def xxtest_040(self):
    cmd = "config --list"
    s = SAT.Sat(self.logger)
    returnCode = s.execute_cli(cmd)
    self.assertTrue(returnCode.isOk())
    logs = self.logger.getLogs()
    self.assertTrue("--value" in logs)

  def test_050(self):
    cmds = SAT.getCommandsList()
    DBG.write("test_050 getCommandsList", cmds)
    for c in cmds:
      cmd = "sat %s --help" % c
      stdout, stderr = SAT.launchSat(cmd)
      self.assertEqual(stderr, "")
      self.assertTrue(c in stdout)
      self.assertTrue("Available options" in stdout)
      
  def test_051(self):
    cmds = SAT.getCommandsList()
    for c in cmds:
      cmd = "%s --help" % c
      s = SAT.Sat(self.logger)
      returnCode = s.execute_cli(cmd)
      self.assertTrue(returnCode.isOk())
      logs = self.logger.getLogsAndClear()
      DBG.write(cmd, logs, True)
      self.assertTrue("Available options" in logs)
                
if __name__ == '__main__':
    unittest.main(exit=False)
    pass
