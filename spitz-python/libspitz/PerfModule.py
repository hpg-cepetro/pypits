#!/usr/bin/env python

# The MIT License (MIT)
#
# Copyright (c) 2017 Caian Benedicto <caian@ggaunicamp.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy 
# of this software and associated documentation files (the "Software"), to 
# deal in the Software without restriction, including without limitation the 
# rights to use, copy, modify, merge, publish, distribute, sublicense, 
# and/or sell copies of the Software, and to permit persons to whom the 
# Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in 
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL 
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER 
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING 
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS 
# IN THE SOFTWARE.

import os, time, timeit, threading, logging, datetime

class PerfModule():
    """
    Performance statistics acquisition module for PY-PITZ. The statistics
    are recorded in the SPITZ log, as well as in a file inside ./perf/. The 
    file is unique for each SPITZ process.

    Available statistics:
      - Number of compute workers
      - Total wall time (since beginning of PerfModule) [us]
      - Total user time (since beginning of PerfModule) [us]
      - Total system time (since beginning of PerfModule) [us]
      - CPU utilization in user mode (min, max, avg) [%]
      - CPU utilization in system mode (min, max, avg) [%]
      - Total CPU utilization (min, max, avg) [%]
      - Resident set size (min, max, avg) [MiB]

    Planned statistics:
      - NVIDIA GPU utilization
      - NVIDIA GPU memory
      - AMD GPU utilization
      - AMD GPU memory

    TODO: 
      - Windows support
    """

    def __init__(self, uid, nw, rinterv, subsamp):
        """
        Constructor.

        Arguments:
          
          uid: The unique ID of the SPITZ process, used when creting the 
          statistics file in ./perf/<UID>-suffix.

          nw: The number of compute workers in the CPU, this is printed in
          the logs and it is not used to normalize any of the statistics.

          rinterv: The report interval, in seconds. Must be an integer greater
          than 1.

          subsamp: The number of steps in between report intervals to acquire
          statistics.
        """

        self.stop = False
        self.uid = uid
        self.nw = nw
        self.rinterv = rinterv
        self.subsamp = subsamp

        logging.info('Starting PerfModule...')

        def runcpu_wrapper():
            self.RunCPU()

        tcpu = threading.Thread(target=runcpu_wrapper)

        try:
            tcpu.daemon = True
        except:
            pass

        try:
            tcpu.setDaemon(True)
        except:
            pass

        tcpu.start()

    def Stop(self):
        """
        Signal the stop of the monitoring thread. This is often not necessary
        because the monitoring thread is created as a daemon
        """
        self.stop = True

    def Dump(self, header, fields, tag, new):
        """
        Print the fields to the perf file.

        Arguments:
          
          header: The header describing fields, it is only written when 
          the file is initialized.

          fields: The statistics collected. They will be trivially converted to 
          string before writing, if any formatting is needed, the field must be 
          previously formatted and passed as string.

          new: Create a new file (or truncate an existing one) and write the 
          header before writing the fields if True, otherwise just append 
          fields.
        """
        dirname = './perf/'
        filename = '%s%s-%s' % (dirname, self.uid, tag)
        mode = 'wt' if new else 'at'
        fields = ' '.join([str(i) for i in fields])

        try:
            os.mkdir(dirname)
        except:
            pass

        try:
            with open(filename, mode) as f:
                if new:
                    f.write(header + '\n')
                f.write(fields + '\n')
        except:
            pass

    def Stat(self, pid):
        """
        Query /proc/PID/stat

        Arguments:
          
          pid: The target process id.

        Return:

          A tuple with the raw RSS, user time and system time

        Note:

          This method will throw exception on failure
        """

        with open('/proc/%d/stat' % pid, 'rt') as f:
            l = f.read()

        # Remove the process name 

        i = l.find('(')
        j = l.rfind(')')

        if i >= 0 and j >= 0:
            l = l[:i] + l[j:]

        l = l.split()

        rss = float(l[23])
        ut = float(l[13])
        st = float(l[14])

        return (rss, ut, st)

    def RunCPU(self):
        """
        CPU Monitoring thread
        """

        # Compute the sleep delay

        delay = float(self.rinterv) / self.subsamp

        # Determine page size

        pagesize = 0

        for pagename in ['SC_PAGESIZE', 'SC_PAGE_SIZE']:
            try:
                pagesize = os.sysconf(pagename)
                break
            except:
                pass

        if pagesize == 0:
            logging.error('PerfModule: Could not determine page size!')
            return

        logging.debug('PerfModule: Page size is %d bytes.' % pagesize)

        # Determine ticks per second

        try:
            ticpersec = os.sysconf(os.sysconf_names['SC_CLK_TCK'])
        except:
            logging.error('PerfModule: Could not determine tick frequency!')
            return

        logging.debug('PerfModule: Tick frequency is %d Hz.' % ticpersec)

        # Get the process PID

        pid = os.getpid()

        # Run the perf module

        logging.info('PerfModule CPU thread started.')

        isnew = True

        refwtime = 0

        lastwtime = 0
        lastutime = 0
        laststime = 0

        while not self.stop:

            minupct = 0
            maxupct = 0
            avgupct = 0

            minspct = 0
            maxspct = 0
            avgspct = 0

            mintpct = 0
            maxtpct = 0
            avgtpct = 0

            minrss = 0
            maxrss = 0
            avgrss = 0

            firstwtime = 0
            firstutime = 0
            firststime = 0

            n = 0

            cpuheader = """# (1) Number of compute workers
# (2) Total wall time (since beginning of PerfModule) [us]
# (3) Total user time (since beginning of PerfModule) [us]
# (4) Total system time (since beginning of PerfModule) [us]
# (5-7) CPU utilization in user mode (min, max, avg) [%]
# (8-10) CPU utilization in system mode (min, max, avg) [%]
# (11-13) Total user + system CPU utilization (min, max, avg) [%]"""

            memheader = """# (1) Total wall time (since beginning of PerfModule) [us]
# (2-4) Resident set size (min, max, avg) [MiB]"""

            for sample in range(self.subsamp):

                if self.stop:
                    break

                try:

                    wt = timeit.default_timer()
                    rss, ut, st = self.Stat(pid)

                    rss = rss * pagesize / 1024 / 1024
                    ut = ut / ticpersec
                    st = st / ticpersec

                    if refwtime == 0:

                        refwtime = wt
                        delta = delay

                        refstamp = datetime.datetime.utcnow()
                        cpuheader = '# ' + \
                            refstamp.strftime('%Y-%m-%d %H:%M:%S.%f') + \
                            '\n' + cpuheader
                        memheader = '# ' + \
                            refstamp.strftime('%Y-%m-%d %H:%M:%S.%f') + \
                            '\n' + memheader

                    else:

                        delta = wt - lastwtime

                        avgrss += rss

                        upd = ut - lastutime
                        spd = st - laststime
                        tpd = upd + spd

                        upc = (upd * 100 / delta)
                        spc = (spd * 100 / delta)
                        tpc = (tpd * 100 / delta)

                        if n == 0:
                            firstwtime = wt
                            firstutime = ut
                            firststime = st
                            minrss = rss
                            maxrss = rss
                            minupct = upc
                            maxupct = upc
                            minspct = spc
                            maxspct = spc
                            mintpct = tpc
                            maxtpct = tpc
                        else:
                            minrss = min(minrss, rss)
                            maxrss = max(maxrss, rss)
                            minupct = min(minupct, upc)
                            maxupct = max(maxupct, upc)
                            minspct = min(minspct, spc)
                            maxspct = max(maxspct, spc)
                            mintpct = min(mintpct, tpc)
                            maxtpct = max(maxtpct, tpc)

                        n += 1

                    lastwtime = wt
                    lastutime = ut
                    laststime = st

                except:
                    # Ignore errors
                    pass

                time.sleep(delay)

            # Something went wrong
            if n == 0:
                continue

            wtime = int((wt - refwtime) * 1000000)
            utime = int(ut * 1000000)
            stime = int(st * 1000000)

            avgrss /= n
            avgupct = ((ut - firstutime) * 100 / (wt - firstwtime))
            avgspct = ((st - firststime) * 100 / (wt - firstwtime))
            avgtpct = ((ut - firstutime + st - firststime) * 100 / (wt - firstwtime))

            if not self.stop:
                self.Dump(cpuheader, [self.nw, wtime, utime, stime, minupct, 
                    maxupct, avgupct, minspct, maxspct, avgspct, mintpct, 
                    maxtpct, avgtpct], 'cpu', isnew)
                self.Dump(memheader, [wtime, minrss, maxrss, avgrss], 'cpumem', isnew)
                isnew = False

        logging.info('PerfModule CPU thread stopped.')
