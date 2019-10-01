*****************
SAT version 5.5.0
*****************

Release Notes, November 2019
============================

.. warning:: This documentation is under construction!

New features and improvments
----------------------------

**pip mode for python modules**

This new mode was introduced in order to simplify the management of the python products (which number is constantly raising years after years...)
It is trigered by two properties within the application configuration file::

    pip : 'yes'
    pip_install_dir : 'python'

The first property activates the use of pip for all the products which have themselves the pip property activated (it concerns twenty products).
The second property specifies that the products should be installed directly in python directory, and not in their own specific directory.
This second property is usefull on windows platform to reduce the length of python path.

After several tests anf iterations, the following management was adopted:
 - sat prepare <application> does nothing for pip products (because at prepare time we don't have python compiled, and the use of native pip may not be compatible).
 - sat compile <application> use the pip module installed in python to get pip archives (wheels), store them in local archive directory, and install then either in python
directory, or in the product directory (in accordance to pip_install_dir property).


**single directory mode**

This new mode was introduced in order to get shorter path on windows platform. It is trigered by the property **single_install_dir**  within the application configuration file::

        single_install_dir : "yes"

When activated, all the products which have themselves the property **single_install_dir** are installed in a common directory, called PRODUCTS.

**Generalisation of sat launcher command**

sat launcher command was extended to generate lauchers based on an executable given as argument with **-e** option::

    sat launcher <application> -n salome.sh -e INSTALL/SALOME/bin/salome.py 

The command generates a launcher called salome.sh, which set the environment, and launch the INSTALL/SALOME/bin/salome.py.


**optimisation of sat compile**

For a complete compilation of salome, sat compile command was spending more than three minutes 
to calculate the dependencies and the order in which the products shoulb be compiled.
The algorithm used was clumsy, and confused.
It was therefore completely rewritten using a topological sorting. 
The products order calculation take now less than one second.

**new management of sections in product configution files**

The sections defined in products are used to specify the variations in the way products are built.
Depending upon the tag or version of the product, sat choose one of these sections and set the product definition according to it.
With time, the number of sections increased a lot. And it is not easy to visualise the differences between these sections, as they often
are identical, except few variations.
With the windows version, new sections are introduced to manage windows specifics.

Therefore the need of a new mode for managing sections arises, that would be simplier, more concise, and help the comprehension. 
This new mode is called **incremental**, and is trigered by the property **incremental** within the default section of the product::

    default:
    {
        ....
        properties:
        {
            incremental : "yes"
        }
        ...
    }

When this mode is defined, the definition of the product is defined incrementaly, by taking into account the reference (the default section) and applying to it corrections defined in the other incremental sections. Depending upon the case several sections may be taken into account, in a predefined order:

* the default section, which contains the reference definition
* on windows platform, the default_win section if it exists
* the section corresponding to the tag. the algorithm to determine this section remains unchanged (what changes is that in incremental mode the section only define deltas, not the complete definition)
* on windows platform, if it exists the same section posfiwed with "_win".

Here is as an example the incremental definition used for boost products. For version 1.49 of boost, we extend the definition because we need to apply a patch::

    default :
    {
        name : "boost"
        build_source : "script"
        compil_script :  $name + $VARS.scriptExtension
        get_source : "archive"
        environ :
        {
           env_script : $name + ".py"
        }
        depend : ['Python' ]
        opt_depend : ['openmpi' ]
        patches : [ ]
        source_dir : $APPLICATION.workdir + $VARS.sep + 'SOURCES' + $VARS.sep + $name
        build_dir : $APPLICATION.workdir + $VARS.sep + 'BUILD' + $VARS.sep + $name
        install_dir : 'base'
        properties :
        {
            single_install_dir : "yes"
            incremental : "yes"
        }
    }

    version_1_49_0:
    {
        patches : [ "boost-1.49.0.patch" ]
    }



Change log
----------

This chapter does not provide the complete set of changes included, only the
most significant changes are listed.


+-------------+-----------------------------------------------------------------------------------+
| Artifact    | Description                                                                       |
+=============+===================================================================================+
| spns #16894 | clean the temp directory at the end of sat package                                |
+-------------+-----------------------------------------------------------------------------------+
| sat #12965  | optimisation of sat compile : better, simplier and faster algo for dependencies!  |
+-------------+-----------------------------------------------------------------------------------+
| sat # 17206 | Use pip to manage python modules                                                  |
+-------------+-----------------------------------------------------------------------------------+
| sat #17137  | check_install functionality improvement : uses linux expending shell rules and    |
|             | interprets environment variables                                                  |
+-------------+-----------------------------------------------------------------------------------+
| sat #8544   | Update and improvement of documentation                                           |
+-------------+-----------------------------------------------------------------------------------+
| sat # 8547  | Generalisation of sat launcher command (new option --exe to specify which exe     |
|             | should be launched after setting the environment                                  |
+-------------+-----------------------------------------------------------------------------------+
| sat #17357  | New field in application pyconf "rm_rpoducts" to blacklist some products          |
+-------------+-----------------------------------------------------------------------------------+
| sat #17194  | Parametrication of the value of INSTALL and BINARIES directories                  |
|             | (in src/internal_config/salomeTools.pyconf)                                       |
+-------------+-----------------------------------------------------------------------------------+
| sat #17639  | Warning when sat is launcher with python3                                         |
+-------------+-----------------------------------------------------------------------------------+
| sat #17359  | New incremental mode for the definition of products                               |
+-------------+-----------------------------------------------------------------------------------+
|             |                                                                                   |
+-------------+-----------------------------------------------------------------------------------+