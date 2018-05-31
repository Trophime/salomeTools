#!/usr/bin/env python
#-*- coding:utf-8 -*-

# This script is used to build the application module.
# First, it copies the content of the sources directory to the install directory.
# Then it runs 'lrelease' to build the resources.

import src.utilsSat as UTS

def compil(config, builder, logger):
    builder.prepare()
    if not builder.source_dir.smartcopy(builder.install_dir):
        raise Exception(_("Error when copying %s sources to install dir") % builder.product_info.name)
    
    # test lrelease #.pyconf needs in ..._APPLI pre_depend : ['qt']
    env = builder.build_environ.environ.environ
    command = "which lrelease" 
    res = UTS.Popen(command, shell=True ,env=env, logger=logger)
    if not res.isOk():
        return res
    
    # run lrelease
    command = "lrelease *.ts"
    cwd = str(builder.install_dir + "resources")
    res = UTS.Popen(command, shell=True, cwd=cwd, env=env, logger=logger)
    return res
