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

import src.debug as DBG # Easy print stderr (for DEBUG only)
import src.pyconf as PYF # 0.3.7
import config_0_3_9.config as PYF9 # TODO 0.3.9

_EXAMPLES = {
1 : """\
  messages:
  [
    {
      stream : "sys.stderr" # modified
      message: 'Welcome'
      name: 'Harry'
    }
    {
      stream : "sys.stdout" # modified
      message: 'Welkom'
      name: 'Ruud'
    }
    {
      stream : $messages[0].stream
      message: 'Bienvenue'
      name: "Yves"
    }
  ]
""",

2 : """\
  aa: 111
  bb: $aa + 222
""",

3 : """\
  aa: Yves
  bb: "Herve" # avoid Hervé -> 'utf8' codec can't decode byte
""",

4 : """\
  aa: Yves
  bb: "Hervé" # avoid Hervé -> 'utf8' codec can't decode byte
""",


}


class TestCase(unittest.TestCase):
  "Test the pyconf.py"""
  
  def test_000(self):
    # one shot setUp() for this TestCase
    # DBG.push_debug(True)
    # SAT.setNotLocale() # test english
    return

  def test_010(self):
    # pyconf.py doc example 0.3.7
    # https://www.red-dove.com/config-doc/ is 0.3.9 !
    # which, when run, would yield the console output:

    expected = """\
Welcome, Harry
Welkom, Ruud
Bienvenue, Yves
"""
    inStream = DBG.InStream(_EXAMPLES[1])
    cfg = PYF.Config(inStream)
    res = ''
    for m in cfg.messages:
        res += '%s, %s\n' % (m.message, m.name)
    self.assertEqual(res, expected)
    outStream = DBG.OutStream()
    cfg.__save__(outStream) # sat renamed save() in __save__()
    res = outStream.value
    DBG.write("test_010 cfg", res)
    self.assertTrue("name : 'Harry'" in res)
    self.assertTrue("name : 'Ruud'" in res)
    self.assertTrue("name : 'Yves'" in res)
        
  def test_020(self):
    cfg = PYF.Config()
    self.assertEqual(str(cfg), '{}')
    self.assertEqual(cfg.__repr__(), '{}')
    cfg.aa = "1111"
    self.assertEqual(str(cfg), "{'aa': '1111'}")
    cfg.bb = 2222
    self.assertTrue("'bb': 2222" in str(cfg))
    self.assertTrue("'aa': '1111'" in str(cfg))
    cfg.cc = 3333.
    self.assertTrue("'cc': 3333." in str(cfg))
    
  def test_030(self):
    inStream = DBG.InStream(_EXAMPLES[2])
    cfg = PYF.Config(inStream)
    self.assertEqual(str(cfg),  "{'aa': 111, 'bb': $aa + 222}")
    self.assertEqual(cfg.aa, 111)
    self.assertEqual(cfg.bb, 333)
      
  def test_040(self):
    inStream = DBG.InStream(_EXAMPLES[3])
    cfg = PYF.Config(inStream)
    self.assertEqual(cfg.aa, "Yves")
    self.assertEqual(cfg.bb, "Herve")
    self.assertEqual(type(cfg.bb), str)
    cfg.bb = "Hervé" # try this
    self.assertEqual(type(cfg.bb), str)
    self.assertEqual(cfg.bb, "Hervé")
    
  def test_045(self):
    """TODO: make Hervé valid with pyconf.py as 0.3.9"""
    inStream = DBG.InStream(_EXAMPLES[4])
    cfg = PYF9.Config(inStream)
    outStream = DBG.OutStream()
    cfg.save(outStream) # sat renamed save() in __save__()
    res = outStream.value
    DBG.write("test_045 cfg", res)
    self.assertTrue("aa : 'Yves'" in res)
    self.assertTrue(r"bb : 'Herv\xc3\xa9'" in res)
    self.assertEqual(cfg.bb, "Hervé")
      
  def test_999(self):
    # one shot tearDown() for this TestCase
    # SAT.setLocale() # end test english
    # DBG.pop_debug()
    return
    
if __name__ == '__main__':
    unittest.main(exit=False)
    pass
