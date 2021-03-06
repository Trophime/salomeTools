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
import platform
import unittest

from src.salomeTools import Sat
from unittestpy.tools import outRedirection

class TestCase(unittest.TestCase):
    """sat config --value"""
    
    def test_010(self):
        # Test the display of the right value of "sat config -v VARS.hostname"
        OK = "KO"

        # output redirection
        my_out = outRedirection()

        # The command to test
        sat = Sat()
        sat.config('-v VARS.hostname')

        # stop output redirection
        my_out.end_redirection()

        # get results
        res = my_out.read_results()

        if platform.node() in res:
            OK = "OK"
        self.assertEqual(OK, "OK")

    def test_020(self):
        # Test the display of the right value of "sat config -l"
        OK = "KO"

        # output redirection
        my_out = outRedirection()

        # The command to test
        sat = Sat()
        sat.config('-l')

        # stop output redirection
        my_out.end_redirection()

        # get results
        res = my_out.read_results()

        # get results
        if "ERROR" not in res:
            OK = "OK"
        self.assertEqual(OK, "OK")
    
    """    
    def test_030(self):
        # Test the exception when salomeTools.pyconf has errors           
        OK = "KO"
        
        # The command to test
        sat = Sat()
        sat.config()
        
        salomeToolspyconfPath = os.path.join(sat.cfg.VARS.srcDir, "internal_config", "salomeTools.pyconf")
        salomeToolspyconfPath_save = os.path.join(sat.cfg.VARS.srcDir, "internal_config", "salomeTools.pyconf_save")
        if os.path.exists(salomeToolspyconfPath_save):
            os.remove(salomeToolspyconfPath_save)
        shutil.copyfile(salomeToolspyconfPath, salomeToolspyconfPath_save)
        f_read = open(salomeToolspyconfPath, 'r')
        text = f_read.read()
        f_read.close()
        os.remove(salomeToolspyconfPath)
        f_write = open(salomeToolspyconfPath, 'w')
        f_write.write(text.replace(':', ''))
        f_write.close()
        
        try:
            sat.config()
        except TypeError:
            OK = "OK"
        finally:
            shutil.copyfile(salomeToolspyconfPath_save, salomeToolspyconfPath)
            os.remove(salomeToolspyconfPath_save)
        self.assertEqual(OK, "OK")
    """       
        
# test launch
if __name__ == '__main__':
    unittest.main()
    pass
