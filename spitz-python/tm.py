#!/usr/bin/env python

#  tm.py
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

from libspitz import JobBinary, SimpleEndpoint
from libspitz import Listener, TaskPool
from libspitz import messaging, config

import Args
import sys, os, datetime, logging, multiprocessing, struct, time

try:
    import Queue as queue # Python 2
except:
    import queue # Python 3

# Global configuration parameters
tm_addr = None # Bind address
tm_port = None # Bind port
tm_nw = None # Maximum number of workers
tm_conn_timeout = None # Socket connect timeout
tm_recv_timeout = None # Socket receive timeout
tm_send_timeout = None # Socket send timeout

###############################################################################
# Parse global configuration
###############################################################################
def parse_global_config(argdict):
    global tm_addr, tm_port, tm_nw, tm_conn_timeout, \
        tm_recv_timeout, tm_send_timeout

    def as_int(v):
        if v == None:
            return None
        return int(v)

    def as_float(v):
        if v == None:
            return None
        return int(v)

    tm_addr = argdict.get('tmaddr', '0.0.0.0')
    tm_port = int(argdict.get('tmport', config.spitz_tm_port))
    tm_nw = int(argdict.get('nw', multiprocessing.cpu_count()))
    if tm_nw <= 0:
        tm_nw = multiprocessing.cpu_count()
    tm_conn_timeout = as_float(argdict.get('ctimeout', config.conn_timeout))
    tm_recv_timeout = as_float(argdict.get('rtimeout', config.recv_timeout))
    tm_send_timeout = as_float(argdict.get('stimeout', config.send_timeout))

###############################################################################
# Configure the log output format
###############################################################################
def setup_log():
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers = []
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(threadName)s - '+
        '%(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    root.addHandler(ch)

###############################################################################
# Abort the aplication with message
###############################################################################
def abort(error):
    logging.critical(error)
    exit(1)

###############################################################################
# Server callback
###############################################################################
def server_callback(conn, addr, port, job, tpool, cqueue):
    logging.info('Connected to %s:%d.', addr, port)

    try:
        # Read the type of message
        mtype = conn.ReadInt64(tm_recv_timeout)

        # Termination signal
        if mtype == messaging.msg_terminate:
            logging.info('Received a kill signal from %s:%d.',
                addr, port)
            os._exit(0)

        # Job manager is trying to send tasks to the task manager
        if mtype == messaging.msg_send_task:
            # Two phase pull: test-try-pull
            while not tpool.Full():
                # Task pool is not full, start asking for data
                conn.WriteInt64(messaging.msg_send_more)
                taskid = conn.ReadInt64(tm_recv_timeout)
                tasksz = conn.ReadInt64(tm_recv_timeout)
                task = conn.Read(tasksz, tm_recv_timeout)
                logging.info('Received task %d from %s:%d.',
                    taskid, addr, port)

                # Try enqueue the received task
                if not tpool.Put(taskid, task):
                    # For some reason the pool got full in between
                    # (shouldn't happen)
                    logging.warning('Rejecting task %d because ' +
                        'the pool is ful!', taskid)
                    conn.WriteInt64(messaging.msg_send_rjct)

            # Task pool is full, stop receiving tasks
            conn.WriteInt64(messaging.msg_send_full)

        # Job manager is querying the results of the completed tasks
        elif mtype == messaging.msg_read_result:
            taskid = None
            try:
                # Dequeue completed tasks until cqueue fires
                # an Empty exception
                while True:
                    # Pop the task
                    taskid, r, res = cqueue.get_nowait()

                    logging.info('Sending task %d to committer %s:%d...',
                        taskid, addr, port)

                    # Send the task
                    conn.WriteInt64(taskid)
                    conn.WriteInt64(r)
                    if res == None:
                        conn.WriteInt64(0)
                    else:
                        conn.WriteInt64(len(res))
                        conn.Write(res)

                    # Wait for the confirmation that the task has
                    # been received by the other side
                    ans = conn.ReadInt64(messaging.msg_read_result)
                    if ans != messaging.msg_read_result:
                        logging.warning('Unknown response received from '+
                            '%s:%d while committing task!', addr, port)
                        raise messaging.MessagingError()

                    taskid = None

            except queue.Empty:
                # Finish the response
                conn.WriteInt64(messaging.msg_read_empty)

            except:
                # Something went wrong while sending, put
                # the last task back in the queue
                if taskid != None:
                    cqueue.put((taskid, r, res))
                    logging.info('Task %d put back in the queue.', taskid)
                pass

        # Unknow message received or a wrong sized packet could be trashing
        # the buffer, don't do anything
        else:
            logging.warning('Unknown message received \'%d\'!', mtype)

    except messaging.SocketClosed:
        logging.info('Connection to %s:%d closed from the other side.',
            addr, port)

    except TimeoutError:
        logging.warning('Connection to %s:%d timed out!', addr, port)

    except:
        logging.warning('Error occurred while reading request from %s:%d!',
            addr, port)

    conn.Close()
    logging.info('Connection to %s:%d closed.', addr, port)

###############################################################################
# Initializer routine for the worker
###############################################################################
def initializer(cqueue, job, argv):
    logging.info('Initializing worker...')
    return job.spits_worker_new(argv)

###############################################################################
# Worker routine
###############################################################################
def worker(state, taskid, task, cqueue, job, argv):
    logging.info('Processing task %d...', taskid)

    # Execute the task using the job module
    r, res, ctx = job.spits_worker_run(state, task, taskid)

    logging.info('Task %d processed.', taskid)

    if res == None:
        logging.error('Task %d did not push any result!', taskid)
        return

    if ctx != taskid:
        logging.error('Context verification failed for task %d!', taskid)
        return

    # Enqueue the result
    cqueue.put((taskid, r, res[0]))

###############################################################################
# Run routine
###############################################################################
def run(argv, job):
    # Create a work pool and a commit queue
    cqueue = queue.Queue()
    tpool = TaskPool(tm_nw, initializer, worker, (cqueue, job, argv))

    # Create the server
    logging.info('Starting network listener...')
    l = Listener(tm_addr, tm_port, server_callback, (job, tpool, cqueue))

    # Start the server and wait for work
    l.Start()
    logging.info('Waiting for work...')
    l.Join()

###############################################################################
# Main routine
###############################################################################
def main(argv):
    # Setup logging
    setup_log()
    logging.debug('Hello!')

    # Print usage
    if len(argv) <= 1:
        abort('USAGE: tm [args] module [module args]')

    # Parse the arguments
    args = Args.Args(argv)
    parse_global_config(args.args)

    # Load the module
    module = args.margs[0]
    job = JobBinary(module)

    # Remove JM arguments when passing to the module
    margv = args.margs

    # Start the tm
    run(margv, job)

    # Finalize
    logging.debug('Bye!')
    #exit(r)

###############################################################################
# Entry point
###############################################################################
if __name__ == '__main__':
    main(sys.argv)
