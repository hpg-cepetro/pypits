#!/usr/bin/env python

#  TaskPool.py
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

import threading, sys, logging

try:
    import Queue as queue # Python 2
except:
    import queue # Python 3

class TaskPool(object):
    """description of class"""

    def __init__(self, max_threads, overfill, initializer, worker, user_args):
        self.max_threads = max_threads
        self.user_args = user_args
        self.initializer = initializer
        self.worker = worker
        self.tasks = queue.Queue(maxsize=max_threads + overfill)
        self.threads = [threading.Thread(target=self.runner) for
            i in range(max_threads)]

        for t in self.threads:
            t.start()

    def runner(self):
        state = None
        try:
            # Initialize the module worker
            state = self.initializer(*self.user_args)
        except:
            # TODO better exception handling
            pass
        while True:
            # Pick a task from the queue and execute it
            # TODO better tm kill
            taskid, task = self.tasks.get()
            try:
                self.worker(state, taskid, task, *self.user_args)
            except:
                logging.error('The worker crashed while processing ' +
                    'the task %d', taskid)

    def Put(self, taskid, task):
        try:
            self.tasks.put_nowait((taskid, task))
        except queue.Full:
            return False
        return True

    def Full(self):
        return self.tasks.full()
