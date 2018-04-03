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

"""\
The Options class that manages the access to all options passed as 
parameters in salomeTools command lines
"""

import getopt
import sys
import pprint as PP

import src
import src.debug as DBG # Easy print stderr (for DEBUG only)

class OptResult(object):
    """
    An instance of this class will be the object manipulated
    in code of all salomeTools commands
    The aim of this class is to have an elegant syntax to manipulate the options.
    
    example: 
      >> print(options.level)
      >> 5
    """
    def __init__(self):
        '''Initialization
        '''
        self.__dict__ = dict()

    def __getattr__(self, name):
        '''Overwrite of the __getattr__ function 
           to customize it for option usage
        
        :param name str: The attribute to get the value.
        :return: the value corresponding to the attribute.
        :rtype: str,int,list,boolean,level
        '''
        if name in self.__dict__:
            return self.__dict__[name]
        else:
            raise AttributeError("--" + name + _(u" is not a valid option"))

    def __setattr__(self, name, value):
        '''Overwrite of the __setattr__ function 
           to customize it for option usage
        
        :param name str: The attribute to set.
        :param value str: The value  corresponding to the attribute.
        :return: Nothing.
        :rtype: N\A
        '''
        object.__setattr__(self, name, value)

    def __repr__(self):
        aStr = PP.pformat(self.__dict__)
        res = "%s(\n %s\n)" % (self.__class__.__name__, aStr[1:-1])
        return res

class Options(object):
    '''Class to manage all salomeTools options
    '''
    def __init__(self):
        '''Initialization
        '''
        # The options field stocks all options of a command 
        # in a list that contains dicts
        self.options = []
        # The list of available option type
        self.availableOptions = "boolean string int float long list list2, level".split()
        self.default = None
        self.results = {}

    def add_option(self, shortName, longName,
                    optionType, destName, helpString="", default = None):
        '''Method to add an option to a command. It gets all attributes
           of an option and append it in the options field
        
        :param shortName str: The short name of the option
                              (ex "l" for level option).
        :param longName str: The long name of the option 
                             (ex "level" for level option).
        :param optionType str: The type of the option (ex "int").
        :param destName str: The name that will be used in the code.
        :param helpString str: The text to display 
                               when user ask for help on a command.     
        :return: Nothing.
        :rtype: N\A
        '''
        tmp = [o['shortName'] for o in self.options if o['shortName'] != '']
        if shortName in tmp: 
          raise Exception("option '-%s' existing yet" % shortName)
        tmp = [o['longName'] for o in self.options if o['longName'] != '']
        if longName in tmp: 
          raise Exception("option '--%s' existing yet" % longName)

        option = dict()
        option['shortName'] = shortName
        option['longName'] = longName

        if optionType not in self.availableOptions:
            print("error optionType", optionType, "not available.")
            sys.exit(src.KOSYS)

        option['optionType'] = optionType
        option['destName'] = destName
        option['helpString'] = helpString
        option['result'] = default
        
        self.options.append(option)
        
    def getDetailOption(self, option):
        """for convenience 
        returns (shortName, longName, optionType, helpString')
        """
        oos = option['shortName']
        ool = option['longName']
        oot = option['optionType']
        ooh = option['helpString']
        return (oos, ool, oot, ooh)


    def get_help(self):
        '''Method that returns all options stored in self.options 
        as help message colored string
        
        :return: colored string
        :rtype: N\A
        '''
        msg = ""
        # Do nothing if there are no options
        if len(self.options) == 0:
            return _("No available options.")

        # for all options, gets its values. 
        # "shortname" is an mandatory field of the options, could be '' 
        msg += "<header>" + _("Available options are:") + "<reset>"
        for option in self.options:
            oos, ool, oot, ooh = self.getDetailOption(option)
            if len(oos) > 0:
                msg += "\n -%1s, --%s (%s)\n" % (oos, ool, oot)
            else:
                msg += "\n --%s (%s)\n" % (ool, oot)
                
            msg += "%s\n" % self.indent(ooh, 10)
        return msg
        
    def indent(self, text, amount, car=" "):
        """indent multi lines message"""
        padding = amount * car
        return ''.join(padding + line for line in text.splitlines(True))
               

    def parse_args(self, argList=None):
        '''Method that instantiates the class OptResult 
           that gives access to all options in the code
        
        :param argList list: the raw list of arguments that were passed
        :return: optResult, args : optResult is the option instance 
                                   to manipulate in the code. args 
                                   is the full raw list of passed options 
        :rtype: (class 'common.options.OptResult',list)
        '''
        # see https://pymotw.com/2/getopt/
        if argList is None:
            argList = sys.argv[1:]
        
        DBG.write("parse_args", argList)
        # DBG.write("options", self.options)
        # format shortNameOption and longNameOption 
        # to make right arguments to getopt.getopt function
        shortNameOption = ""
        longNameOption = []
        for option in self.options:
            shortNameOption = shortNameOption + option['shortName']
            if option['shortName'] != "" and option['optionType'] != "boolean":
                shortNameOption = shortNameOption + ":"

            if option['longName'] != "":
                if option['optionType'] != "boolean":
                    longNameOption.append(option['longName'] + "=")
                else:
                    longNameOption.append(option['longName'])

        # call to getopt.getopt function to get the option 
        # passed in the command regarding the available options
        try:
          optlist, args = getopt.getopt(argList, shortNameOption, longNameOption)
        except Exception as e:
          msg = str(e) + "\n\n" + self.get_help()
          raise Exception(msg)

        # instantiate and completing the optResult that will be returned
        optResult = OptResult()
        for option in self.options:
            shortOption = "-" + option['shortName']
            longOption = "--" + option['longName']
            optionType = option['optionType']
            for opt in optlist:
                if opt[0] in [shortOption, longOption]:
                    if optionType == "string":
                        option['result'] = opt[1]
                    elif optionType == "boolean":
                        option['result'] = True
                    elif optionType == "int":
                        option['result'] = int(opt[1])
                    elif optionType == "float":
                        option['result'] = float(opt[1])
                    elif optionType == "long":
                        option['result'] = long(opt[1])
                    elif optionType == "list":
                        if option['result'] is None:
                            option['result'] = list()
                        option['result'].append(opt[1])
                    elif optionType == "level": #logger logging levels
                        option['result'] = opt[1]
                        # TODO test in (lowercase) debug info warning error critical
                    elif optionType == "list2":
                        if option['result'] is None:
                            option['result'] = list()
                        if opt[1].find(",") == -1:
                            option['result'].append(opt[1])
                        else:
                            elts = filter(lambda l: len(l) > 0, opt[1].split(","))
                            option['result'].extend(elts)

            optResult.__setattr__(option['destName'], option['result'])
            # free the option in order to be able to make 
            # a new free call of options (API case)
            option['result'] = None

        self.results = {"optlist": optlist, "optResult": optResult, "args": args, "argList": argList}
        DBG.write("results", self.results)
        return optResult, args

    def __repr__(self): 
        '''repr for only self.options and self.results (if present)
        '''
        aDict = {'options': self.options, 'results': self.results}
        aStr = PP.pformat(aDict)
        res = "%s(\n %s\n)" % (self.__class__.__name__, aStr[1:-1])
        return res
        
    def __str__(self): 
        '''str for only resume expected self.options
        '''
        #aDict = [(k["longName"], k["shortName", k["helpString"]) for k in self.options}
        #aList = [(k, self.options[k]) for k in sorted(self.options.keys())]
        aDict = {}
        for o in self.options:
          aDict[o["longName"]] = (o["shortName"], o["helpString"])
        aStr = PP.pformat(aDict)
        res = "%s(\n %s)" % (self.__class__.__name__, aStr[1:-1])
        return res
        
    def debug_write(self):
        DBG.write("options and results", self, True)


