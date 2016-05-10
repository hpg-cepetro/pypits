#!/usr/bin/env python

#  JobBinary.py
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

import ctypes, os, struct, sys, logging

# TODO try-except around C calls

class JobBinary(object):
    """Class binding for the external job binary loaded by spitz"""

    # Constructor
    def __init__(self, filename):
        filename = os.path.realpath(filename)
        self.filename = filename
        self.module = ctypes.CDLL(filename)

        # Create the return type for the *new functions, otherwise
        # it will assume int as return instead of void*
        rettype_new = ctypes.c_void_p

        self._spits_job_manager_new = self.module.spits_job_manager_new
        self._spits_job_manager_new.restype = rettype_new;

        self.module.spits_job_manager_new.restype = rettype_new;
        self.module.spits_worker_new.restype = rettype_new;
        self.module.spits_committer_new.restype = rettype_new;

        # Create the c function for the runner callback
        self.crunner = ctypes.CFUNCTYPE(
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_longlong))

        # Create the c function for the pusher callback
        self.cpusher = ctypes.CFUNCTYPE(
            None,
            ctypes.c_void_p,
            ctypes.c_longlong,
            ctypes.c_void_p)

    def c_argv(self, argv):
        # Encode the string to byte array
        argv = [x.encode('utf8') for x in argv]

        # Cast the C arguments
        cargc = ctypes.c_int(len(argv))
        cargv = (ctypes.c_char_p * len(argv))()
        cargv[:] = argv
        return cargc, cargv

    def bytes(self, it):
        try:
            if bytes != str:
                return bytes(it)
        except:
            pass
        return struct.pack('%db' % len(it), *it)

    def unbyte(self, s):
        try:
            if bytes != str:
                return s
        except:
            pass
        return struct.unpack('%db' % len(s), s)

    def to_c_array(self, it):
        # Cover the case where an empty array or list is passed
        if it == None or len(it) == 0:
            return ctypes.c_void_p(None), 0
        # Normal C allocation
        cit = (ctypes.c_byte * len(it))()
        cit[:] = self.unbyte(it)
        citsz = ctypes.c_longlong(len(it))
        return cit, citsz

    def to_py_array(self, v, sz):
        v = ctypes.cast(v, ctypes.POINTER(ctypes.c_byte))
        return self.bytes(v[0:sz])
        

    def spits_main(self, argv, runner):
        # Call the runner if the job does not have an initializer
        if not hasattr(self.module, 'spits_main'):
            return runner(len(argv), argv, module, None)

        # Create an inner converter for the callback
        def run(argc, argv, data, size):
            # Convert argc/argv back to a string list
            pargv = [argv[i].decode('utf8') for i in range(0, argc)]

            # Run the runner code
            r, pdata = runner(pargv)

            # Convert the data result to a C pointer/size
            if pdata == None:
                data[0] = None
                size[0] = 0
            else:
                cdata = (ctypes.c_byte * len(pdata))()
                cdata[:] = self.unbyte(pdata)
                data[0] = ctypes.cast(cdata, ctypes.c_void_p)
                size[0] = len(pdata)

            return r

        # Cast the C arguments
        cargc, cargv = self.c_argv(argv)
        crun = self.crunner(run)

        # Call the C function
        return self.module.spits_main(cargc, cargv, crun)

    def spits_job_manager_new(self, argv):
        # Cast the C arguments
        cargc, cargv = self.c_argv(argv)

        return ctypes.c_void_p(self._spits_job_manager_new(cargc, cargv))

    def spits_job_manager_next_task(self, user_data):
        # Create the pointer to task and task size
        ctask = ctypes.c_void_p()
        ctasksz = ctypes.c_longlong()

        # Get the next task
        r = self.module.spits_job_manager_next_task(user_data,
            ctypes.pointer(ctask), ctypes.pointer(ctasksz))

        # Convert the task to python
        task = self.to_py_array(ctask, ctasksz.value)

        return r, task

    def spits_job_manager_finalize(self, user_data):
        # Optional function
        if not hasattr(self.module, 'spits_job_manager_finalize'):
            return

        # Is expected that the framework will not mess with the
        # value inside user_data do its ctype will remain unchanged
        return self.module.spits_job_manager_finalize(user_data)

    def spits_worker_new(self, argv):
        # Cast the C arguments
        cargc, cargv = self.c_argv(argv)

        return ctypes.c_void_p(self.module.spits_worker_new(cargc, cargv))

    def spits_worker_run(self, user_data, task, taskctx):
        res = [None, None, None]

        # Create the pointer to task and task size
        ctask, ctasksz = self.to_c_array(task)

        # Create an inner converter for the callback
        def push(cres, cressz, ctx):
            # Thanks to python closures, the context is not 
            # necessary, in any case, check for correctness
            res[1] = (self.to_py_array(cres, cressz),)
            res[2] = ctx

        # Run the task
        res[0] = self.module.spits_worker_run(user_data, ctask, ctasksz, 
            self.cpusher(push), ctypes.c_void_p(taskctx))

        return res

    def spits_worker_finalize(self, user_data):
        # Optional function
        if not hasattr(self.module, 'spits_worker_finalize'):
            return

        # Is expected that the framework will not mess with the
        # value inside user_data do its ctype will remain unchanged
        return self.module.spits_worker_finalize(user_data)

    def spits_committer_new(self, argv):
        # Cast the C arguments
        cargc, cargv = self.c_argv(argv)

        return ctypes.c_void_p(self.module.spits_committer_new(cargc, cargv))

    def spits_committer_commit_pit(self, user_data, result):
        # Create the pointer to result and result size
        cres, cressz = self.to_c_array(result)

        return self.module.spits_committer_commit_pit(user_data, cres, cressz)

    def spits_committer_commit_job(self, user_data, jobctx):
        fres = [None, None, None]

        # Create an inner converter for the callback
        def push(cfres, cfressz, ctx):
            # Thanks to python closures, the context is not 
            # necessary, in any case, check for correctness
            fres[1] = (self.to_py_array(cfres, cfressz),)
            fres[2] = ctx

        # Commit job and get the final result
        fres[0] = self.module.spits_committer_commit_job(user_data,
            self.cpusher(push), ctypes.c_void_p(jobctx))

        return fres

    def spits_committer_finalize(self, user_data):
        # Optional function
        if not hasattr(self.module, 'spits_committer_finalize'):
            return

        # Is expected that the framework will not mess with the
        # value inside user_data do its ctype will remain unchanged
        return self.module.spits_committer_finalize(user_data)
