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
import src
import src.debug as DBG # Easy print stderr (for DEBUG only)

class TestCase(unittest.TestCase):
  "Test the sat --help commands"""
  
  def test_000(self):
    # one shot setUp() for this TestCase
    # DBG.push_debug(True)
    SAT.setNotLocale() # test english

  def test_010(self):
    cmd = "sat --help"
    stdout, stderr = SAT.launchSat(cmd)
    self.assertEqual(stderr, "")
    self.assertTrue(" - config" in stdout)

  def test_011(self):
    cmd = "--help"
    s = SAT.Sat(cmd)
    exitCode = s.execute_command()
    self.assertEqual(src.okToStr(exitCode), "OK")
    
  def test_030(self):
    cmd = "sat --help config"
    stdout, stderr = SAT.launchSat(cmd)
    self.assertEqual(stderr, "")
    self.assertTrue("--value" in stdout)

  def test_031(self):
    cmd = "--help config"
    s = SAT.Sat(cmd)
    exitCode = s.execute_command()
    self.assertEqual(src.okToStr(exitCode), "OK")
      
  def test_012(self):
    cmd = "config -l"
    s = SAT.Sat(cmd)
    exitCode = s.execute_command()
    self.assertEqual(src.okToStr(exitCode), "OK")
  
  def test_040(self):
    cmds = SAT.getCommandsList()
    for c in cmds:
      cmd = "sat --help %s" % c
      stdout, stderr = SAT.launchSat(cmd)
      self.assertEqual(stderr, "")
      # DBG.write("stdout '%s'" % cmd, stdout)
      self.assertTrue("vailable options" in stdout)
      
  def test_999(self):
    # one shot tearDown() for this TestCase
    SAT.setLocale() # end test english
    # DBG.pop_debug()
      
if __name__ == '__main__':
    unittest.main(exit=False)
    pass
