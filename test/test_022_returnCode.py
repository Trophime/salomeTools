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
import pprint as PP

import src.debug as DBG
from src.returnCode import ReturnCode as RC

verbose = False # True

class TestCase(unittest.TestCase):
  "Test the debug.py"""
  
  def test_000(self):
    # one shot setUp() for this TestCase
    if verbose:
      DBG.push_debug(True)
      DBG.write("assert unittest", [a for a in dir(self) if "assert" in a])
    pass
  
  def test_010(self):
    rc = RC()
    self.assertFalse(rc.isOk())
    rrc = str(rc)
    DBG.write("test_010 str", rrc)
    self.assertIn("ND:", rrc)
    self.assertIn("No given explanation", rrc)
    self.assertNotIn("for value", rrc)
    rrc = repr(rc)
    DBG.write("test_010 repr", rrc)
    self.assertIn("ND:", rrc)
    self.assertIn("No given explanation", rrc)
    self.assertIn("for value", rrc)
       
  def test_015(self):
    rc = RC("OK", "all is good")
    self.assertTrue(rc.isOk())
    rrc = str(rc)
    DBG.write("test_015 str", rrc)
    self.assertIn("OK:", rrc)
    self.assertIn("all is good", rrc)
    self.assertNotIn("for value", rrc)
    rrc = repr(rc)
    DBG.write("test_015 repr", rrc)
    self.assertIn("OK:", rrc)
    self.assertIn("all is good", rrc)
    self.assertIn("Not set", rrc)
    aVal = "I am a value result"
    rc.setValue(aVal)
    self.assertTrue(rc.isOk())
    self.assertEqual(rc.getValue(), aVal)
    rrc = repr(rc)
    DBG.write("repr", rrc)
    
  def test_020(self):
    aVal = "I am a value result"
    rc1 = RC("OK", "all is good1", aVal + "1")
    self.assertTrue(rc1.isOk())
    rc2 = RC("OK", "all is good2", aVal + "2")
    self.assertTrue(rc2.isOk())
    rc3 = rc1 + rc2
    self.assertTrue(rc3.isOk())
    rrc = repr(rc3)
    DBG.write("test_020 repr", rrc)
    self.assertIn("OK:", rrc)
    self.assertIn("good1", rrc)
    self.assertIn("good2", rrc)
    self.assertIn("result1", rrc)
    self.assertIn("result2", rrc)
    rc4 = rc3 + rc1
    rrc = repr(rc4)
    DBG.write("test_020 repr", rrc)
    self.assertEqual(len(rc4.getWhy()), 3)
    self.assertEqual(len(rc4.getValue()), 3)
    
  def test_025(self):
    rc0 = RC("KO")
    aVal = "I am a value result"
    rc1 = RC("OK", "all is good1", aVal + "1")
    self.assertTrue(rc1.isOk())
    rc1.setStatus("KO") # change status raz why and value
    self.assertFalse(rc1.isOk())
    print rc0
    print rc1
    self.assertEqual(repr(rc0), repr(rc1))
    
    rc1 = RC("OK", "all is good1", aVal + "1")
    rc2 = rc0 + rc1 + rc1 + rc0 + rc1
    DBG.write("test_025 repr", rc2, True)
    rrc = repr(rc2)
    self.assertIn("KO:", rrc)
          
  def test_999(self):
    # one shot tearDown() for this TestCase
    if verbose:
      DBG.pop_debug()
    return
    
if __name__ == '__main__':
    unittest.main(exit=False)
    pass

