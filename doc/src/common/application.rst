************
APPLICATIONS
************

The **application** is the key notion in SAT. Most of the SAT commands take an
application as mandatory argument.

An application is basically a set of **products**. referenced by their name and
their version. An application is described by its pyconf config file.

Here is an example of an application config file :

.. code-block:: python

   #!/usr/bin/env python
   #-*- coding:utf-8 -*-
   
   APPLICATION :
   {
       name : 'SALOME-master'
       workdir : $LOCAL.workdir + $VARS.sep + $APPLICATION.name + '-' + $VARS.dist
       tag : 'master'
       environ :
       {
           build : {CONFIGURATION_ROOT_DIR : $workdir + $VARS.sep + "SOURCES" + $VARS.sep + "CONFIGURATION"}
       }
       products :
       {
           # PREREQUISITES :
           Python : '2.7.10'
           Cython : '0.23.2'
           numpy : '1.9.2'
           scipy : '0.15.1'
           lapack : '3.5.0'
           cmake : '3.5.2'
           pyreadline : '2.0'
           setuptools : '0.6c11'
           markupsafe : '0.23'
           Jinja2 : '2.7.3'
           six : '1.9.0'
           distribute : '0.6.28'
           pytz : '2014.10'
           pyparsing : '1.5.6'
           dateutil : '2.4.0'
           freetype : '2.4.11'
           matplotlib : '1.4.3'
           cppunit : '1.13.2'
           qt : '5.6.1-1'
           PyQt : '5.6'
           qwt : '6.1.2'
           sip : '4.18'
           omniORB : '4.1.6'
           omniORBpy : '3.6'
           boost : '1.58.0'
           swig : '2.0.8'
           gl2ps : '1.3.9p1'
           freeimage : '3.16.0'
           tcl : '8.6.0'
           tk : '8.6.0'
           libxml2 : '2.9.0'
           CAS : 'V7_1_0p1'
   
           hdf5 : '1.8.14'
           ParaView : {section : 'version_5_1_2plus_820', tag : '5.1.2plus'}
           metis : '5.1.0'
           scotch : '5.1.12b'
           med : '3.2.1'
   
           graphviz : '2.38.0p1'
           doxygen : '1.8.3.1'
           docutils : '0.12'
           Sphinx : '1.2.3'
           Pygments : '2.0.2'
           opencv : '2.4.6.1'
           Homard : '11.8'
           netgen : '5.3.1'
           MeshGems : '2.5-3'
           cgns : '3.1.3-4'
   
           lata : '1.3p3'
   
           # SALOME MODULES :
           'CONFIGURATION'
           'SALOME' : "Vmaster"
   
           'MEDCOUPLING'
           'LIBBATCH' : "V2_3_1"
           'KERNEL'
           'GUI'
   
           'GEOM'
   
       }
       profile :
       {
           product : "SALOME"
       }
       test_base : 
       {
           name : "SALOME"
           tag : "SalomeV8"
       }
   }


