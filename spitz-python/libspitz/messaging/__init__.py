#!/usr/bin/env python

#  __init__.py
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

from .SocketClosed import SocketClosed
from .MessagingError import MessagingError

import select

# Messaging codes

msg_send_task = 0x0201
msg_send_more = 0x0202
msg_send_full = 0x0203
msg_send_rjct = 0x0204

msg_read_result = 0x0101
msg_read_empty = 0x0000

msg_terminate = 0xFFFF

# Signal the spitz system through the upper 32
# bits of the result variable that an error
# occurred with the function call itself
res_module_error = 0xFFFFFFFF00000000
res_module_noans = 0xFFFFFFFE00000000
res_module_ctxer = 0xFFFFFFFD00000000

# Definition of the recv method for sockets, considering
# a definite size and timeout
def recv(conn, size, timeout):
    r = None
    left = size
    while left > 0:
        ready = select.select([conn], [], [], timeout)
        if not ready[0]:
            raise TimeoutError()
        d = conn.recv(left)
        if len(d) == 0:
            raise SocketClosed()
        r = r + d if r else d
        left = size - len(r)
    return r
