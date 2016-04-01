#!/usr/bin/env python

#  Args.py
#
#  Copyright (C) 2015 Caian Benedicto <caian@ggaunicamp.com>
#
#  This file is part of Spitz
#
#  Spitz is free software; you can redistribute it and/or modify it
#  under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  Spitz is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

class Args(object):
    """Simple argument processor"""

    # Constructor
    def __init__(self, args):
        self.args = {}

        for i, arg in enumerate(args[1:]):
            # Stop the first non -- arg
            if arg.find('--') != 0:
                break;

            # Split the argument
            j = arg.find('=')
            if j <= 2:
                raise Exception()
            a = arg[2:j]
            v = arg[j+1:]

            # Save the dictionary
            self.args[a] = v

        self.margs = args[i+1:]
