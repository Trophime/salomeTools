#!/usr/bin/env python
#-*- coding:utf-8 -*-
#  Copyright (C) 2010-2013  CEA/DEN
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

"""
Contains all the stuff that can change with the architecture 
on which SAT is running
"""

import os
import sys
import platform

def is_windows():
    """Checks windows OS
      
    :return: (bool) True if system is Windows
    """
    return platform.system() == 'Windows'

def get_user():
    """Gets the username that launched sat  
    
    :return: (str) environ var USERNAME
    """
    # In windows case, the USERNAME environment variable has to be set
    if is_windows():
        if not os.environ.has_key('USERNAME'):
            raise Exception('USERNAME environment variable not set')
        return os.environ['USERNAME']
    else: # linux
        import pwd
        return pwd.getpwuid(os.getuid())[0]

def _lsb_release(args):
    """Get system information with lsb_release.
    
    :param args: (str) The CLI arguments to give to lsb_release.
    :return: (str) The distribution.
    """
    try:
        path = '/usr/local/bin:/usr/bin:/bin'
        lsb_path = os.getenv("LSB_PATH")
        if lsb_path is not None:
            path = lsb_path + ":" + path
        
        from subprocess import Popen, PIPE
        p = Popen(['lsb_release', args], env={'PATH': path}, stdout=PIPE)
        res = p.communicate()[0][:-1]
        # in case of python3, convert byte to str
        if isinstance(res, bytes):
            res = res.decode()
        return res
    except OSError:
        msg = _("""\
lsb_release not installed.
You can define $LSB_PATH to give the path to lsb_release""")
        raise Exception(msg)

def get_distribution(codes):
    """Gets the code for the distribution
    
    :param codes: (L{Mapping}) 
      The map containing distribution correlation table.
    :return: (str)
      The distribution on which salomeTools is running, regarding the 
      distribution correlation table contained in codes variable.
    """
    if is_windows():
        return "Win"

    # Call to lsb_release
    distrib = _lsb_release('-si')
    if codes is not None and distrib in codes:
        distrib = codes[distrib]
    else:
        msg = _("""\
Unknown distribution: '%s'
Please add your distribution to src/internal_config/distrib.pyconf.""") % distrib
        raise Exception(msg)

    return distrib


def get_distrib_version(distrib, codes):
    """Gets the version of the distribution
    
    :param distrib: (str) 
      The distribution on which the version will be found.
    :param codes: (L{Mapping}) 
      The map containing distribution correlation table.
    :return: (str)
      The version of the distribution on which 
      salomeTools is running, regarding the distribution 
      correlation table contained in codes variable.
    """

    if is_windows():
        return platform.release()

    # Call to lsb_release
    version = _lsb_release('-sr')
    if distrib in codes:
        if version in codes[distrib]:
            version = codes[distrib][version]

    if distrib == "CO":
        version=version[0]  #for centos, we only care for major version
    return version

def get_python_version():
    """Gets the version of the running python.
    
    :return: (str) The version of the running python.
    """
    
    # The platform python module gives the answer
    return platform.python_version()

def get_nb_proc():
    """
    Gets the number of processors of the machine 
    on which salomeTools is running.
    
    :return: (str) The number of processors.
    """
    
    try :
        import multiprocessing
        nb_proc=multiprocessing.cpu_count()
    except :
        nb_proc=int(os.sysconf('SC_NPROCESSORS_ONLN'))
    return nb_proc
