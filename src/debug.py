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

'''This file is to assume print debug messages sys.stderr for salomeTools
warning: only for SAT development phase
'''

import sys
import pprint as PP

_debug = [False] #support push/pop for temporary active outputs

def indent(text, amount=2, ch=' '):
    padding = amount * ch
    return ''.join(padding + line for line in text.splitlines(True))

def write(title, var="", force=None):
    """write sys.stderr a message if _debug[-1]==True or optionaly force=True"""
    fmt = "\n#### DEBUG: %s:\n%s\n"
    if _debug[-1] or force:
        if type(var) is not str:
          sys.stderr.write(fmt % (title, indent(PP.pformat(var))))
        else:
          sys.stderr.write(fmt % (title, indent(var)))
    return

def push_debug(aBool):
    """set debug outputs activated, or not"""
    _debug.append(aBool)

def pop_debug():
    """restore previous debug outputs status"""
    if len(_debug) > 1:
        return _debug.pop()
    else:
        sys.stderr.write("\nERROR: pop_debug: too much pop.")
        return None
