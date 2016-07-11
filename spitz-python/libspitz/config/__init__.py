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

send_timeout = None
recv_timeout = None
conn_timeout = None

send_backoff = 0.25
recv_backoff = 2

spitz_jm_port = 7726
spitz_tm_port = 7727

mode_tcp = 'tcp'
mode_uds = 'uds'