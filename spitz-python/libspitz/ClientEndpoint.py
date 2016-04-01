#!/usr/bin/env python

#  ClientEndpoint.py
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

from .SimpleEndpoint import SimpleEndpoint
from libspitz import messaging

import socket

class ClientEndpoint(SimpleEndpoint):
    """Message exchange class with a client"""

    def __init__(self, address, port, conn):
        SimpleEndpoint.__init__(self, address, port)
        self.socket = conn

    def Open(self, timeout):
        pass

    def Read(self, size, timeout):
        return messaging.recv(self.socket, size, timeout)

    def Write(self, data):
        self.socket.sendall(data)

    def Close(self):
        if self.socket != None:
            self.socket.close()
            self.socket = None
