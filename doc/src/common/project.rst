*******
PROJECT
*******

In SAT, the largest notion is the notion of **project**, which includes the following:

- a set of **applications** <application.rst>, 

- a set of **products** <product.rst>,

- a set of archives for the **products** <product.rst>,

- a set of jobs,

- a set of machines (for the jobs).

In practical terms, a project is a pyconf file where the five variables 
corresponding to the previous list are defined.

Example :

.. code-block:: python

    #!/usr/bin/env python
    #-*- coding:utf-8 -*-

    project_path : "/home/salome/SPN_PRIVATE/SAT5/SALOME-PROJECT/"

    # Where to search the archives of the products
    ARCHIVEPATH : "/data/tmpsalome/salome/prerequis/archives"
    # Where to search the pyconf of the applications
    APPLICATIONPATH : "/home/salome/SPN_PRIVATE/sat5dev_Applications/"
    # Where to search the pyconf of the products
    PRODUCTPATH : $project_path + "products/"
    # Where to search the pyconf of the jobs of the project
    JOBPATH : $project_path + "jobs/"
    # Where to search the pyconf of the machines of the project
    MACHINEPATH : $project_path + "machines/"

    git_info :
    {
        default_git_server : "http://git.salome-platform.org/gitpub/"
        default_git_server_dev : "ssh://gitolite3@git.salome-platform.org/"
    }

    test_bases :
    [
          {
            name : 'SALOME'
            get_sources : 'git'
            info :
            {
              base : '/home/salome/GitRepo/TestBases.git'
            }
          }
    ]
