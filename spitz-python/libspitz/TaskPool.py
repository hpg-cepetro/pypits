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

    def __init__(self, max_threads, initializer, worker, user_args):
        self.max_threads = max_threads
        self.user_args = user_args
        self.lock = threading.Lock()
        self.tasks = queue.Queue()
        self.initializer = initializer
        self.worker = worker
        self.active = 0
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
            self.dec()

    def test(self):
        return self.active < self.max_threads

    def inc(self):
        success = False
        self.lock.acquire()
        if self.test():
            self.active += 1
            success = True
        self.lock.release()
        return success

    def dec(self):
        self.lock.acquire()
        if self.active > 0:
            self.active -= 1
        self.lock.release()

    def Put(self, taskid, task):
        if self.inc():
            self.tasks.put((taskid, task))
            return True
        else:
            return False

    def Full(self):
        return not self.test()
