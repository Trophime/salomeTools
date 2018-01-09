#!/usr/bin/env python
#-*- coding:utf-8 -*-

# %% LICENSE_SALOME_CEA_BEGIN
# Copyright (C) 2008-2018  CEA/DEN
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
# %% LICENSE_END

import os
import gettext
import unittest

verbose = False

class TestCase(unittest.TestCase):
 
  def test_005(self):
    # load resources for internationalization
    gettext.install('salomeTools', os.path.realpath(os.path.dirname(__file__))) 
    res = _("Georges says '%(1)s' for %(2)s.") % {"1": "hello", "2": "test"}
    if verbose: print(res)
    self.assertEqual(res, "pour test Hervé dit 'hello'.")

if __name__ == '__main__':
  verbose = False
  unittest.main()
  pass
