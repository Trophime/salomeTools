#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2008-20xx  CEA/DEN
# 
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
# 
# See http://www.salome-platform.org or email : webmaster.salome@opencascade.com

import unittest

import src.debug as DBG # Easy print stderr (for DEBUG only)
from src.catchAll import CatchAll as CA

verbose = False # True #

########################################################################################
class TestCase(unittest.TestCase):
  "Test the catchAll.py"""
  
  def test_000(self):
    # one shot setUp() for this TestCase
    if verbose:
      DBG.push_debug(True)
      # DBG.write("assert unittest", [a for a in dir(self) if "assert" in a])
    pass
  
  def test_999(self):
    # one shot tearDown() for this TestCase
    if verbose:
      DBG.pop_debug()
    return

  def test_005(self):
    a = CA()
    a.tintin = "reporter"
    a.milou = "dog"
    a._yoo = "abcd" # not in repr
    self.assertEqual(a.tintin, "reporter")
    self.assertEqual(a.milou, "dog")
    DBG.write("test_005 str", str(a))
    DBG.write("test_005 repr", repr(a))
    DBG.write("test_005 jsondump", a.jsonDumps())
    del(a.tintin)
    self.assertFalse(hasattr(a, "tintin"))
    self.assertEqual(a.milou, "dog")
    self.assertIn("_yoo", a.__dict__.keys())

    
  def test_010(self):
    h = CA()
    h.haddock = "sailor"
    h.tintin = "reporter"
    h.milou = "dog"
    h._yoo = "abcd" # not in repr
    aDict = {1: "1", 2: "22", 10: "1000000000"}
    # long for indent view
    h.other = ["castafiore", 
               "nestor", 
               "irmaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
               aDict]
    a = CA()
    a.heroes = h
    DBG.write("test_010 str", str(a))
    DBG.write("test_010 repr", repr(a))
    DBG.write("test_010 jsondump", a.jsonDumps())
    r = repr(a)
    self.assertIn("tintin:", r)
    self.assertIn("other:", r)
    self.assertIn("1000000000", r)
    self .assertNotIn("abcd", r) # not in repr
    self .assertEqual(a.heroes._yoo, "abcd") # but in a.heroes
    

if __name__ == '__main__':
    unittest.main(exit=False)
    pass

