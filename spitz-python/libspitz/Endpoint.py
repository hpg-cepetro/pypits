#!/usr/bin/env python

#  Endpoint.py
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
#

import struct

class Endpoint(object):
    """Interface for Network endpoint to exchange messages"""

    def Open(self):
        raise NotImplementedError('Please specialize this class to make a custom endpoint')

    def Read(self, size, timeout):
        raise NotImplementedError('Please specialize this class to make a custom endpoint')

    def Write(self, data):
        raise NotImplementedError('Please specialize this class to make a custom endpoint')

    def ReadInt64(self, timeout):
        return struct.unpack('!q', self.Read(8, timeout))[0]

    def WriteInt64(self, value):
        self.Write(struct.pack('!q', value))

    def Close(self):
        raise NotImplementedError('Please specialize this class to make a custom endpoint')
