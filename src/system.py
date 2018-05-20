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
        p = SP.Popen(cmd, shell=True)
        p.communicate()
        return RCO.ReturnCode("OK", msg)
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
    :return: RCO.ReturnCode OK if the extraction is successful
    """
    if not where.exists():
        where.make()
    whe = str(where)
    if tag == "master" or tag == "HEAD":
        command = "git clone %(rem)s %(whe)s" %  {'rem': from_what, 'whe': whe}
    else:
        # NOTICE: this command only works with recent version of git
        #         because --work-tree does not work with an absolute path
        where_git = os.path.join(whe, ".git" )
        command = r"""\
rmdir %(whe)s && \
git clone %(rem)s %(whe)s && \
git --git-dir=%(whe_git)s --work-tree=%(whe)s checkout %(tag)s"""
        command = command % {'rem': from_what, 'tag': tag, 'whe': whe, 'whe_git': where_git }

    env = environment.environ.environ
    res = UTS.Popen(command, cwd=str(where.dir()), env=env, shell=True, logger=logger)
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
        return True, os.path.commonprefix(archive.getnames())
    except Exception as exc:
        logger.error("archive_extract: %s\n" % exc)
        return False, None

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
    :return: (bool) True if the extraction is successful
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
        command = "cvs -d :%(protocol)s:%(root)s %(command)s -d %(where)s %(tag)s %(product)s" % \
            { 'protocol': protocol, 'root': root, 'where': str(where.base()),
              'tag': opttag, 'product': product, 'command': cmd }
    else:
        command = "cvs -d %(root)s %(command)s -d %(where)s %(tag)s %(base)s/%(product)s" % \
            { 'root': server, 'base': base, 'where': str(where.base()),
              'tag': opttag, 'product': product, 'command': cmd }

    logger.debug(command)

    if not where.dir().exists():
        where.dir().make()

    logger.logTxtFile.write("\n" + command + "\n")
    logger.logTxtFile.flush()        
    res = SP.call(command,
                          cwd=str(where.dir()),
                          env=environment.environ.environ,
                          shell=True,
                          stdout=logger.logTxtFile,
                          stderr=SP.STDOUT)
    return (res == 0)

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
    :return: (bool) True if the extraction is successful
    """
    if not where.exists():
        where.make()

    if checkout:
        command = "svn checkout --username %(user)s %(remote)s %(where)s" % \
            { 'remote': from_what, 'user' : user, 'where': str(where) }
    else:
        command = ""
        if os.path.exists(str(where)):
            command = "/bin/rm -rf %(where)s && " % \
                { 'remote': from_what, 'where': str(where) }
        
        if tag == "master":
            command += "svn export --username %(user)s %(remote)s %(where)s" % \
                { 'remote': from_what, 'user' : user, 'where': str(where) }       
        else:
            command += "svn export -r %(tag)s --username %(user)s %(remote)s %(where)s" % \
                { 'tag' : tag, 'remote': from_what, 'user' : user, 'where': str(where) }
    
    logger.logTxtFile.write(command + "\n")
    
    logger.debug(command)
    logger.logTxtFile.write("\n" + command + "\n")
    logger.logTxtFile.flush()
    res = SP.call(command,
                          cwd=str(where.dir()),
                          env=environment.environ.environ,
                          shell=True,
                          stdout=logger.logTxtFile,
                          stderr=SP.STDOUT)
    return (res == 0)
