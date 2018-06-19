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
import src.debug as DBG # Easy print stderr (for DEBUG only)

import src.linksXml as LIXML

class TestCase(unittest.TestCase):
  "Test the debug.py"""
  
  def test_000(self):
    # one shot setUp() for this TestCase
    DBG.push_debug(False)
    # SAT.setNotLocale() # test english
    return
    
  def test_999(self):
    # one shot tearDown() for this TestCase
    # SAT.setLocale() # end test english
    DBG.pop_debug()
    return
    
  def test_005(self):
    k0 = LIXML.getLinksXml() # get singleton
    DBG.write("LinkXml k1 singleton", k0)
    self.assertEqual(k0.findLink(-1), k0)
    self.assertEqual(k0.findLink(1), None)
    k0.appendLink(1)
    self.assertEqual(k0.findLink(-1), k0)
    self.assertEqual(k0.findLink(1).idName, 1)
    DBG.write("LinkXml k0 singleton", k0)
    
    LIXML.resetLinksXml()
    k00 = LIXML.getLinksXml() # get new singleton
    self.assertEqual(id(k0), id(k00))
    self.assertEqual(k0, k00)
    DBG.write("LinkXml k00 singleton", k00)
    
    self.assertEqual(k00.findLink(1), None)
    k00.appendLink(0)
    k00.appendLink(1)
    self.assertEqual(k00.findLink(-1), k00)
    self.assertEqual(k00.findLink(0).idName, 0)
    self.assertEqual(k00.findLink(1).idName, 1)
    
  def test_010(self):
    k0 = LIXML.getLinksXml() # get singleton
    with self.assertRaises(Exception):
      k0.appendLink(1)
    k0.appendLink(2)
    self.assertEqual(len(k0._linksXml), 3)
    self.assertEqual(k0.findLink(2).idName, 2)
    DBG.write("LinkXml k0 singleton", k0)
    k1 = k0.findLink(1)
    k11 = k1.appendLink(11)
    k2 = k0.findLink(2)
    k21 = k2.appendLink(21)
    k22 = k2.appendLink(22)
    self.assertEqual(k0.findLink(11), k11)
    self.assertEqual(k0.findLink(21), k21)
    self.assertEqual(k0.findLink(22), k22)
    kk = k0.getAllIdNames()
    self.assertEqual(kk, [-1, 0, 1, 11, 2, 21, 22])
    
  def test_015(self):
    k0 = LIXML.getLinksXml() # get singleton
    
    
if __name__ == '__main__':
    unittest.main(exit=False)
    pass

