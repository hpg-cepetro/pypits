#!/usr/bin/env python

#  jm.py
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
from libspitz import messaging, config

import Args
import sys, threading, os, time, ctypes, logging, struct, threading, traceback

# Global configuration parameters
jm_killtms = None # Kill task managers after execution
jm_conn_timeout = None # Socket connect timeout
jm_recv_timeout = None # Socket receive timeout
jm_send_timeout = None # Socket send timeout

###############################################################################
# Parse global configuration
###############################################################################
def parse_global_config(argdict):
    global jm_killtms, tm_addr, tm_port, tm_nw, tm_conn_timeout, \
        tm_recv_timeout, tm_send_timeout

    def as_int(v):
        if v == None:
            return None
        return int(v)

    def as_float(v):
        if v == None:
            return None
        return int(v)

    def as_bool(v):
        if v == None:
            return None
        return bool(v)

    jm_killtms = as_bool(argdict.get('killtms', True))
    jm_conn_timeout = as_float(argdict.get('ctimeout', config.conn_timeout))
    jm_recv_timeout = as_float(argdict.get('rtimeout', config.recv_timeout))
    jm_send_timeout = as_float(argdict.get('stimeout', config.send_timeout))

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
# Parse the definition of a proxy
###############################################################################
def parse_proxy(cmd):
    cmd = cmd.split()

    if len(cmd) != 3:
        raise Exception()

    logging.debug('Proxy %s.' % (cmd[1]))

    name = cmd[1]
    gate = cmd[2].split(':')
    prot = gate[0]
    addr = gate[1]
    port = int(gate[2])

    return (name, { 'protocol' : prot, 'address' : addr, 'port' : port })

###############################################################################
# Parse the definition of a compute node
###############################################################################
def parse_node(cmd, proxies):
    cmd = cmd.split()

    if len(cmd) < 2:
        raise Exception()

    logging.debug('Node %s.' % (cmd[1]))

    name = cmd[1]
    host = name.split(':')
    addr = host[0]
    port = int(host[1])

    # Simple endpoint
    if len(cmd) == 2:
        return (name, SimpleEndpoint(addr, port))

    # Endpoint behind a proxy
    elif len(cmd) == 4:
        if cmd[2] != 'through':
            raise Exception()

        proxy = proxies.get(cmd[3], None)
        if proxy == None:
            raise Exception()

        # Proxies are not supported yet...
        logging.info('Node %s is behind a proxy and will be ignored.' %
            (cmd[1]))
        return None

    # Unknow command format
    raise Exception()

###############################################################################
# Load the list of task managers from a file
###############################################################################
def load_tm_list(filename = None):
    # Override the filename if it is empty
    if filename == None:
        nodefile = 'nodes.txt'
        filename = os.path.join('.', nodefile)

    logging.debug('Loading task manager list from %s...' % (nodefile,))

    # Read all lines
    try:
        with open(filename, 'rt') as file:
            lines = file.readlines()
    except:
        logging.warning('Could not load the list of task managers!')
        return {}

    lproxies = [parse_proxy(x.strip()) for x in lines if x[0:5] == 'proxy']
    proxies = {}

    for p in lproxies:
        if p != None:
            proxies[p[0]] = p[1]

    ltms = [parse_node(x.strip(), proxies) for x in lines if x[0:4] == 'node']
    tms = {}
    for t in ltms:
        if t != None:
            tms[t[0]] = t[1]

    logging.debug('Loaded %d task managers.' % (len(tms),))

    return tms

###############################################################################
# Exchange messages with an endpoint to begin pushing tasks
###############################################################################
def setup_endpoint_for_pushing(e):
    try:
        # Try to connect to a task manager
        e.Open(jm_conn_timeout)

        # Ask if it is possible to send tasks
        e.WriteInt64(messaging.msg_send_task)

        # Wait for a response
        response = e.ReadInt64(jm_recv_timeout)

        if response == messaging.msg_send_full:
            # Task mananger is full
            logging.debug('Task manager at %s:%d is full.',
                e.address, e.port)

        elif response == messaging.msg_send_more:
            # Continue to the task pushing loop
            return True

        else:
            # The task manager is not replying as expected
            logging.error('Unknown response from the task manager!')

    except:
        # Problem connecting to the task manager
        logging.warning('Error connecting to task manager at %s:%d!',
            e.address, e.port)

    e.Close()
    return False

###############################################################################
# Exchange messages with an endpoint to begin reading results
###############################################################################
def setup_endpoint_for_pulling(e):
    try:
        # Try to connect to a task manager
        e.Open(jm_conn_timeout)

        # Ask if it is possible to send tasks
        e.WriteInt64(messaging.msg_read_result)

        return True

    except:
        # Problem connecting to the task manager
        logging.warning('Error connecting to task manager at %s:%d!',
            e.address, e.port)

    e.Close()
    return False

###############################################################################
# Push tasks while the task manager is not full
###############################################################################
def push_tasks(job, jm, tm, taskid, task, tasklist):
    # Keep pushing until finished or the task manager is full
    while True:
        if task == None:
            # Only get a task if the last one was already sent
            taskid += 1
            r1, task = job.spits_job_manager_next_task(jm)

            # Exit if done
            if r1 == 0:
                return (True, 0, None)

            # Add the generated task to the tasklist
            tasklist[taskid] = (0, task)

            logging.debug('Generated task %d.', taskid)

        try:
            logging.debug('Pushing %d...', taskid)

            # Push the task to the active task manager
            tm.WriteInt64(taskid)
            tm.WriteInt64(len(task))
            tm.Write(task)

            # Wait for a response
            response = tm.ReadInt64(jm_recv_timeout)

            if response == messaging.msg_send_full:
                # Task was sent, but the task manager is now full
                task = None
                break

            elif response == messaging.msg_send_more:
                # Continue pushing tasks
                task = None
                pass

            elif response == messaging.msg_send_rjct:
                # Task was rejected by the task manager, this is not
                # predicted for a model where just one task manager
                # pushes tasks, exit the task loop
                logging.warning('Task manager at %s:%d rejected task %d',
                    tm.address, tm.port, taskid)
                break

            else:
                # The task manager is not replying as expected
                logging.error('Unknown response from the task manager!')
                break
        except:
            # Something went wrong with the connection,
            # try with another task manager
            break

    return (False, taskid, task)

###############################################################################
# Read and commit tasks while the task manager is not empty
###############################################################################
def commit_tasks(job, co, tm, tasklist, completed):
    # Keep pulling until finished or the task manager is full
    while True:
        try:
            # Pull the task from the active task manager
            taskid = tm.ReadInt64(jm_recv_timeout)

            if taskid == messaging.msg_read_empty:
                # No more task to receive
                return

            # Read the rest of the task
            r = tm.ReadInt64(jm_recv_timeout)
            ressz = tm.ReadInt64(jm_recv_timeout)
            res = tm.Read(ressz, jm_recv_timeout)

            # Tell the task manager that the task was received
            tm.WriteInt64(messaging.msg_read_result)

            # Warning, exceptions after this line may cause task loss
            # if not handled properly!!

            if r == messaging.res_module_error:
                logging.error('The remote worker crashed while ' +
                    'executing task %d!', r)
            elif r != 0:
                logging.error('The task %d was not successfully executed, ' +
                    'worker returned %d!', taskid, r)

            # Validated completed task

            c = completed.get(taskid, (None, None))
            if c[0] != None:
                # This shouldn't happen without the fault tolerance system!
                logging.warning('The task %d was received more than once!',
                    taskid)

            # Remove it from the tasklist

            p = tasklist.pop(taskid, (None, None))
            if p[0] == None and c[0] == None:
                # The task was not already completed and was not scheduled
                # to be executed, this is serious problem!
                logging.error('The task %d was not in the working list!',
                    taskid)

            r2 = job.spits_committer_commit_pit(co, res)

            if r2 != 0:
                logging.error('The task %d was not successfully committed, ' +
                    'committer returned %d', taskid, r2)

            # Add completed task to list
            completed[taskid] = (r, r2)

        except:
            # Something went wrong with the connection,
            # try with another task manager
            break

###############################################################################
# Job Manager routine
###############################################################################
def jobmanager(argv, job, jm, tasklist, completed):
    logging.info('Job manager running...')

    # Load the list of nodes to connect to
    tmlist = load_tm_list()

    # Task generation loop

    taskid = 0
    task = None
    finished = False

    while True:
        # Reload the list of task managers at each
        # run so new tms can be added on the fly
        try:
            newtmlist = load_tm_list()
            if len(newtmlist) > 0:
                tmlist = newtmlist
            else:
                logging.warning('New list of task managers is ' +
                    'empty and will not be updated!')
        except:
            logging.error('Failed parsing task manager list!')

        for name, tm in tmlist.items():
            logging.debug('Connecting to %s:%d...', tm.address, tm.port)

            # Open the connection to the task manager and query if it is
            # possible to send data
            if not setup_endpoint_for_pushing(tm):
                continue

            logging.debug('Pushing tasks to %s:%d...', tm.address, tm.port)

            # Task pushing loop
            finished, taskid, task = push_tasks(job,
                jm, tm, taskid, task, tasklist)

            # Close the connection with the task manager
            tm.Close()

            logging.debug('Finished pushing tasks to %s:%d.',
                tm.address, tm.port)

            # Exit the task manager loop only if all tasks have been
            # received back from the task managers
            # TODO if finished and len(tasklist) == 0:
            if finished:
                logging.info('All tasks generated.')
                completed[0] = 1
                return

        time.sleep(0.25)

###############################################################################
# Committer routine
###############################################################################
def committer(argv, job, co, tasklist, completed):
    logging.info('Committer running...')

    # Load the list of nodes to connect to
    tmlist = load_tm_list()

    # Result pulling loop
    while True:
        # Reload the list of task managers at each
        # run so new tms can be added on the fly
        try:
            newtmlist = load_tm_list()
            if len(newtmlist) > 0:
                tmlist = newtmlist
            else:
                logging.warning('New list of task managers is ' +
                    'empty and will not be updated!')
        except:
            logging.error('Failed parsing task manager list!')

        for name, tm in tmlist.items():
            logging.debug('Connecting to %s:%d...', tm.address, tm.port)

            # Open the connection to the task manager and query if it is
            # possible to send data
            if not setup_endpoint_for_pulling(tm):
                continue

            logging.debug('Pulling tasks from %s:%d...', tm.address, tm.port)

            # Task pulling loop
            commit_tasks(job, co, tm, tasklist, completed)

            # Close the connection with the task manager
            tm.Close()

            logging.debug('Finished pulling tasks from %s:%d.',
                tm.address, tm.port)

            if len(tasklist) == 0 and completed[0] == 1:
                logging.info('All tasks committed.')
                return

        time.sleep(2)

###############################################################################
# Kill all task managers
###############################################################################
def killtms():
    logging.info('Killing task managers...')

    # Load the list of nodes to connect to
    tmlist = load_tm_list()

    for name, tm in tmlist.items():
        try:
            logging.debug('Connecting to %s:%d...', tm.address, tm.port)

            tm.Open(jm_conn_timeout)
            tm.WriteInt64(messaging.msg_terminate)
            tm.Close()
        except:
            # Problem connecting to the task manager
            logging.warning('Error connecting to task manager at %s:%d!',
                tm.address, tm.port)

###############################################################################
# Run routine
###############################################################################
def run(argv, job):
    # List of pending tasks
    tasklist = {}

    # Keep an extra list of completed tasks
    completed = {0: 0}

    # Start the job manager
    logging.info('Starting job manager...')

    # Create the job manager from the job module
    jm = job.spits_job_manager_new(argv)

    jmthread = threading.Thread(target=jobmanager,
        args=(argv, job, jm, tasklist, completed))
    jmthread.start()

    # Start the committer
    logging.info('Starting committer...')

    # Create the job manager from the job module
    co = job.spits_committer_new(argv)

    cothread = threading.Thread(target=committer,
        args=(argv, job, co, tasklist, completed))
    cothread.start()

    jmthread.join()
    cothread.join()

    # Commit the job
    logging.info('Committing Job...')
    r, res = job.spits_committer_commit_job(co)

    return r, res

###############################################################################
# Main routine
###############################################################################
def main(argv):
    # Setup logging
    setup_log()
    logging.debug('Hello!')

    # Print usage
    if len(argv) <= 1:
        abort('USAGE: jm module [module args]')

    # Parse the arguments
    args = Args.Args(argv)
    parse_global_config(args.args)

    # Load the module
    module = args.margs[0]
    job = JobBinary(module)

    # Remove JM arguments when passing to the module
    margv = args.margs

    # Wrapper to include job module
    def run_wrapper(argv):
        return run(argv, job)

    # Run the module
    logging.info('Running module')
    r = job.spits_main(margv, run_wrapper)

    # Kill the workers
    if jm_killtms:
        killtms()

    # Finalize
    logging.debug('Bye!')
    #exit(r)

###############################################################################
# Entry point
###############################################################################
if __name__ == '__main__':
    main(sys.argv)
