#!/usr/bin/env python
#-*- coding:utf-8 -*-

__doc__="""
Utility for print environment variables

examples: 
  - split all or specific environment variables $XXX(s)...
    >> environs.py -> all
    >> environs.py SHELL PATH -> specific $SHELL $PATH
    
  - split all or specific environment variables on pattern $*XXX*(s)...
    >> environs.py --pat ROOT -> specific $*ROOT* 
    
  - split search specific substrings in contents of environment variables $XXX(s)...
    >> environs.py --grep usr  -> all specific environment variables containing usr

tips:
  - create unix alias as shortcut for bash console
    >> alias envs=".../environs.py"
"""

import sys
import os

def _test_var_args(args):
  for arg in args:
    print "another arg:", arg

def _printOneLineOrNot(i, env):
  splitenv = env[i].split(":")
  done = False
  nb = 20
  for j in splitenv:
    if j!="": 
      if not done: 
        print "{:<30} = {}".format(i, j)
        done=True
      else:
        print "{:<30}   {}".format(" ", j) 
        
def print_split_environs(args=[]):
  env=os.environ
  for i in sorted(env):
      if (len(args)==0) or (i in args):
        _printOneLineOrNot(i, env)

def print_split_pattern_environs(args=[]):
  env=os.environ
  for i in sorted(env):
      ok = False
      for j in args:
        if j in i:
          ok = True
          #print "i %s j %s %s" % (i,j,ok)
      if (len(args)==0) or (ok):
        _printOneLineOrNot(i, env)

def print_grep_environs(args=[]):
  env=os.environ
  for i in sorted(env):
      for j in env[i].split(":"):
        for a in args:
          if a in j:
            #print i+" contains  "+j
            print '{:<20}    contains {}'.format(i,j)
            

if __name__ == '__main__':
  import sys
  args=sys.argv[1:]
  if len(args)<1:
    print_split_environs()
  elif args[0] in ["-h","--help"]: 
    print __doc__
  elif args[0] in ["-g","--grep"]: 
    print_grep_environs(args[1:])
  elif args[0] in ["-p","--pat"]: 
    print_split_pattern_environs(args[1:])
  else:
    print_split_environs(args)

