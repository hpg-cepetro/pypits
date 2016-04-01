#!/usr/bin/env python

#  SimpleEndpoint.py
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

from .Endpoint import Endpoint
from libspitz import messaging

import socket, logging

class SimpleEndpoint(Endpoint):
    """Simple message exchange class"""

    def __init__(self, address, port):
        self.address = address
        self.port = port
        self.socket = None

    def Open(self, timeout):
        if self.socket:
            return

        if self.port <= 0:
            # Create an Unix Data Socket instead of a
            # normal TCP socket
            try:
                socktype = socket.AF_UNIX
            except AttributeError:
                logging.error('The system does not support ' +
                    'Unix Domain Sockets')
                raise
            sockaddr = self.address

        else:
            # Create a TCP socket
            socktype = socket.AF_INET
            sockaddr = (self.address, self.port)

        self.socket = socket.socket(socktype, socket.SOCK_STREAM)
        self.socket.settimeout(timeout)
        self.socket.connect(sockaddr)

    def Read(self, size, timeout):
        return messaging.recv(self.socket, size, timeout)

    def Write(self, data):
        self.socket.sendall(data)

    def Close(self):
        if self.socket != None:
            self.socket.close()
            self.socket = None
