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
All utilities method doing a system call, 
like open a browser or an editor, or call a git command

| Usage:
| >> import src.system as SYSS
"""

import os
import tarfile
import subprocess as SP

import utilsSat as UTS
import src.returnCode as RCO
import src.debug as DBG

def show_in_editor(editor, filePath, logger):
    """open filePath using editor.
    
    :param editor: (str) The editor to use.
    :param filePath: (str) The path to the file to open.
    """
    # default editor is vi
    if editor is None or len(editor) == 0:
        editor = 'vi'
    
    if '%s' not in editor:
        editor += ' %s'

    try:
        # launch cmd using subprocess.Popen
        cmd = editor % filePath
        msg = "show_in_editor command: '%s'" % cmd
        logger.debug(msg)
        res = UTS.Popen(cmd, logger=logger)
        return res
    except:
        msg = _("Unable to edit file '%s'") % filePath
        logger.error(msg)
        return RCO.ReturnCode("KO", msg)


def git_extract(from_what, tag, where, logger, environment=None):
    """Extracts sources from a git repository.
    
    :param from_what: (str) The remote git repository.
    :param tag: (str) The tag.
    :param where: (str) The path where to extract.
    :param logger: (Logger) The logger instance to use.
    :param environment: (Environ) 
      The environment to source when extracting.
    :return: (ReturnCode) OK if the extraction is successful
    """
    if not where.exists():
      where.make()
    whe = str(where)
    where_git = os.path.join(whe, ".git" )
    command = r"""
set -x 
aDir=%(whe)s
rmdir $aDir
git clone %(rem)s $aDir --quiet
cd $aDir
git checkout %(tag)s --quiet
# last command for OK/KO
git log -n 1
""" % {'rem': from_what, 'tag': tag, 'whe': whe }

    env = environment.environ.environ
    res = UTS.Popen(command, cwd=str(where.dir()), env=env, logger=logger)
    DBG.write("git_extract", res.__repr__())
    return res

def archive_extract(from_what, where, logger):
    """Extracts sources from an archive.
    
    :param from_what: (str) The path to the archive.
    :param where: (str) The path where to extract.
    :param logger: (Logger) The logger instance to use.
    :return: (bool) True if the extraction is successful
    """
    try:
      archive = tarfile.open(from_what)
      for i in archive.getmembers():
        archive.extract(i, path=str(where))
      value = os.path.commonprefix(archive.getnames())
      res = RCO.ReturnCode("OK", "archive_extract done", value=value)
    except Exception as e:
      logger.error("<KO> archive_extract problem:\n%s" % str(e))
      res = RCO.ReturnCode("KO", "archive_extract problem", value=str(e))
    return res

def cvs_extract(protocol, user, server, base, tag, product, where,
                logger, checkout=False, environment=None):
    """Extracts sources from a cvs repository.
    
    :param protocol: (str) The cvs protocol.
    :param user: (str) The user to be used.
    :param server: (str) The remote cvs server.
    :param base: (str) .
    :param tag: (str) The tag.
    :param product: (str) The product.
    :param where: (str) The path where to extract.
    :param logger: (Logger) The logger instance to use.
    :param checkout: (bool) If true use checkout cvs.
    :param environment: (Environ) 
      The environment to source when extracting.
    :return: (ReturnCode) OK if the extraction is successful
    """

    opttag = ''
    if tag is not None and len(tag) > 0:
      opttag = '-r ' + tag

    cmd = 'export'
    if checkout:
      cmd = 'checkout'
    elif len(opttag) == 0:
      opttag = '-DNOW'
    
    if len(protocol) > 0:
      root = "%s@%s:%s" % (user, server, base)
      command = r"""
set -x 
aDir=%(whe)s
cvs -d :%(prot)s:%(root)s %(cmd)s -d $aDir %(tag)s %(prod)s
# last command for OK/KO
cd $aDir
""" % { 'prot': protocol, 'root': root, 'whe': str(where.base()),
        'tag': opttag, 'prod': product, 'cmd': cmd }
    else:
      command = r"""
set -x 
aDir=%(whe)s
cvs -d %(root)s %(cmd)s -d $aDir %(tag)s %(base)s/%(prod)s
# last command for OK/KO
cd $aDir
""" % { 'root': server, 'base': base, 'whe': str(where.base()),
       'tag': opttag, 'prod': product, 'cmd': cmd }

    if not where.dir().exists():
      where.dir().make()

    env = environment.environ.environ
    res = UTS.Popen(command, cwd=str(where.dir()), env=env, logger=logger)
    DBG.write("cvs_extract", res.__repr__())
    return res

def svn_extract(user,
                from_what,
                tag,
                where,
                logger,
                checkout=False,
                environment=None):
    """Extracts sources from a svn repository.
    
    :param user: (str) The user to be used.
    :param from_what: (str) The remote git repository.
    :param tag: (str) The tag.
    :param where: (str) The path where to extract.
    :param logger: (Logger) The logger instance to use.
    :param checkout: (bool) If true use checkout svn.
    :param environment: (Environ)
      The environment to source when extracting.
    :return: (ReturnCode) OK if the extraction is successful
    """
    if not where.exists():
      where.make()
      
    repl = {
      'rem': from_what,
      'user': user, 
      'whe': str(where),
      'tag' : tag,
    }
    
    if checkout:
      cmd = "svn checkout --username %(user)s %(rem)s $aDir" %  repl
    else:
      cmd = ""
      if os.path.exists(str(where)):
        cmd = "rm -rf $aDir\n" % repl
      if tag == "master":
        cmd += "svn export --username %(user)s %(rem)s $aDir" % repl      
      else:
        cmd += "svn export -r %(tag)s --username %(user)s %(rem)s $aDir" % repl
        
    cmd = """
set -x 
aDir=%(whe)s
%s
# last command for OK/KO
cd $aDir
""" % cmd
    env = environment.environ.environ
    res = UTS.Popen(cmd, cwd=str(where.dir()), env=env, logger=logger)
    DBG.write("svn_extract", res.__repr__())
    return res

