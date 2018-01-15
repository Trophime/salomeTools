#!/usr/bin/env python
# -*- coding: utf-8 -*-

# %% LICENSE_SALOME_CEA_BEGIN
# Copyright (C) 2008-2016  CEA/DEN
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


"""
test all SAT unittest files (test*.py) existing in subdirectories of a root directory

example:
  AllTestLauncherSat.py --rootPath='.' --pattern='test*.py'
"""

"""
#### base of algorithm functionality

#see http://www.voidspace.org.uk/python/articles/introduction-to-unittest.shtml

import unittest

import test_something
import test_something2
import test_something3

loader = unittest.TestLoader()

suite = loader.loadTestsFromModule(test_something)
suite.addTests(loader.loadTestsFromModule(test_something2))
suite.addTests(loader.loadTestsFromModule(test_something3))

runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)

#### and so...
"""


import os
import sys
import unittest
import argparse as AP

import glob
import fnmatch
import pprint as PP #pretty print

debug = False
verboseImport = True

def errPrint(aStr):
  """to avoid write in html or xml file log message"""
  sys.stderr.write(aStr + '\n')

try:
  import test.unittestpy.HTMLTestRunner as HTST
except:
  HTST = None
  errPrint("""
WARNING: no HTML output available.
         try find 'test/unittestpy/HTMLTestRunner.py'.
""")


try:
  import xmlrunner as XTST
except:
  XTST = None
  errPrint("""
WARNING: no XML output available.
         try 'pip install unittest-xml-reporting'.
""")


###################################################################
def locate(pattern, root=os.curdir):
  """
  Locate all files matching supplied filename pattern in and below
  supplied root directory.
  """
  result = []
  for path, dirs, files in os.walk(os.path.abspath(root)):
    for filename in fnmatch.filter(files, pattern):
      result.append( os.path.join(path, filename) )
  return result

def printEnv(search=""):
  """
  list all environment variables which name contains search string
  example: 
    import AllTestLauncher as ATL
    ATL.printEnv("ROOT_")
  """
  env=os.environ
  for i in sorted(env):
    if search in i:
      print i 

def grepInEnv(search=""):
  """
  list all environment variables which contains search string
  example: 
    import AllTestLauncher as ATL
    ATL.grepInEnv("XDATA")
  """
  env=os.environ
  for i in sorted(env):
     done=False
     for j in env[i].split(":"):
       if search in j:
           if not done:
             print i+" contains " 
             done=True
           print "  "+j
      

###################################################################
def runOnArgs(args):
  """
  launch tests on args.pattern files
  """
  fromFileOrPath = args.rootPath
  fileTestPattern = args.pattern
  if fromFileOrPath == None:
    directory, name = os.path.split( os.path.realpath( __file__ ) )
  else:
    if os.path.isdir(fromFileOrPath):
      directory, name = (fromFileOrPath, None)
      fileTestPatternCurrent = fileTestPattern
    elif os.path.isfile(fromFileOrPath):
      directory, name = os.path.split( os.path.realpath( fromFileOrPath ) )
      fileTestPatternCurrent = name
    else:
      mess = "Cannot get file or directory '%s'" % fromFileOrPath
      errPrint("ERROR: " + mess)
      return None
      #raise Exception("Cannot get file or directory '%s'" % fromFileOrPath)

  #files = glob.glob(os.path.join(directory, "*Test.py"))
  files = sorted(locate(fileTestPatternCurrent, directory))

  filesForTest={}

  for aFile in files:
    aDir, aName = os.path.split(aFile)
    aImport, ext = os.path.splitext(aName)
    
    try:
      if aFile in filesForTest.keys():
        print "WARNING: imported yet: "+aFile
      else:
        sys.path.insert(0, aDir)
        done = True
        if verboseImport: errPrint("try import '%s'" % aImport)
        aModule = __import__(aImport, globals(), locals(), []) 
        del sys.path[0]
        done = False
        filesForTest[aFile] = (aImport, aModule)
    except:
      if done: 
        del sys.path[0] #attention of sys.path appends
        done = False
      errPrint("ERROR: AllTestLauncher: import '%s'" % aFile)
      continue

  listfilesForTest = sorted(filesForTest.keys())
  result = None

  errPrint("AllTestLauncher test files:\n %s" % PP.pformat(listfilesForTest))
  
  if len(listfilesForTest) == 0: 
    if debug: errPrint("WARNING: AllTestLauncher: empty list of test files")
    return None

  loader = unittest.TestLoader()
  suite = None

  for i,k in enumerate(listfilesForTest):
    if debug: errPrint("Test: %s %s" % (i, k))
    if i == 0:
      suite = loader.loadTestsFromModule( filesForTest[k][1] )
      pass
    else:
      suite.addTests( loader.loadTestsFromModule( filesForTest[k][1] ) )
      pass

  if args.type == "std": 
    runner = unittest.TextTestRunner(verbosity=args.verbosity)
  elif args.type == "html": 
    runner = HTST.HTMLTestRunner(verbosity=args.verbosity, )
  elif args.type == "xml": 
    if args.name == 'stdout':
      #all-in-one xml output at 'sys.stdout' for pipe redirection
      runner = XTST.XMLTestRunner(verbosity=args.verbosity, output=sys.stdout)
    else:
      #one file xml per test in suite in args.name directory
      runner = XTST.XMLTestRunner(verbosity=args.verbosity, output=args.name)
  else:
    errPrint("ERROR: unknown type of output: '%s'" % args.type)
    return None    
    
  if suite != None: result = runner.run(suite)
  return result

###################################################################
def runFromEnvVar(envVar, fileTestPattern="*Test.py"):
  """
  example: 
    import AllTestLauncher as ATL
    ATL.runFromEnvVar("MICROGEN_ROOT_DIR")
    ATL.runFromEnvVar("MICROGEN_ROOT_DIR", "aggregate_*GJKTest.py")
  """
  env=os.environ
  res = []
  for i in sorted(env):
    if envVar in i:
      res.append(i)
  if len(res) > 1:
    mess = "multiple environment variable for '%s': %s" % (envVar, str(res))
    errPrint("ERROR: " + mess)
    return None
  if len(res) < 1:
    mess = "no environment variable for '%s'" % (envVar)
    errPrint("ERROR: " + mess)
    return None
  res = res[0]
  tmp = env[res].split(":")
  if len(tmp) > 1:
    mess = "need only one path in environment variable '%s'" % (res)
    errPrint("ERROR: " + mess)
    return None  
  run(fromFileOrPath=env[res], fileTestPattern=fileTestPattern)


###################################################################
def getParser():
  parser = AP.ArgumentParser(description='launch All SAT python tests', argument_default=None)

  parser.add_argument(
    '-d', '--debug', 
    help='set debug mode, more verbose',
    action='store_true',
  )
  parser.add_argument(
    '-v', '--verbosity', 
    help='set verbosity of unittests [0|1|2...]',
    default=2,
    metavar='int'
  )
  parser.add_argument(
    '-r', '--rootPath', 
    help='''\
dir name with absolute or relative path stand for root directory
of recursive searching unittest python files
''',
    default='.',
   metavar='dirPath'
  )
  parser.add_argument(
    '-p', '--pattern', 
    help="file pattern for unittest files ['test_*.py'|'*Test.py'...]",
    default="test_*.py",
    metavar='filePattern'
  )
  parser.add_argument(
    '-t', '--type', 
    help="type of output: ['std'(standart ascii)|'xml'|'html']",
    default="std",
    choices=['std', 'xml', 'html'],
    metavar='outputType'
  )
  parser.add_argument(
    '-n', '--name', 
    help="""(only for type xml)
name of directory output: ['test_reports'|...].
If name = 'stdout' then all-in-one xml output at 'sys.stdout'. For pipe redirection:
'>> AllTestLauncher.py -t xml -n stdout > tmp.xml'
""",
    default="test_reports",
    metavar='dirName'
  )
  return parser

#export PATH=/volatile/wambeke/SAT5/SAT5_S840_MATIX24/salomeTools-5-cvw:${PATH}

###################################################################
if __name__ == '__main__':
  args = getParser().parse_args(sys.argv[1:])
  debug = args.debug
  directory = os.path.realpath(args.rootPath)
  if debug: print("INFO: args:\n  %s" % PP.pformat(args))
  sys.path.insert(0, directory) #supposed to be root of a package
  runOnArgs(args)
  del sys.path[0]



