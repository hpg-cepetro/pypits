import logging
import sys
import traceback

_memstat_enabled = False
_can_enable = True

try:
    import resource
    import gc
    import base64
    import os
    import inspect
except:
    logging.warning('could not import the modules necessary to memstat, disabling')
    _memstat_enabled = False
    _can_enable = False

def disable():
    global _memstat_enabled
    _memstat_enabled = False

def enable():
    global _memstat_enabled, _can_enable
    if not _can_enable:
        logging.warning('could not enable memstat')
    else:
        _memstat_enabled = True

def isenabled():
    global _memstat_enabled
    return _memstat_enabled

def stats():
    global _memstat_enabled, _can_enable
    if not _memstat_enabled:
        return
    if not _can_enable:
        logging.warning('could not enable memstat')
        _memstat_enabled = False
        return
    try:
        s0, s1, s2 = gc.get_count()
        usage = resource.getrusage(resource.RUSAGE_SELF)
        kb = usage.ru_maxrss
        _frame = inspect.currentframe()
        frame = _frame.f_back
        fname = frame.f_code.co_filename
        fnum = frame.f_lineno
        logging.info('memstat:%s:%d: rss_kb: %d gb_stages: %d %d %d' % \
                     (fname, fnum, kb, s0, s1, s2))
    except:
        print(sys.exc_info())
        traceback.print_exc()
        logging.warning('something went wrong with memstat, disabling')
        _can_enable = False
        _memstat_enabled = False
    finally:
        # Necessary to avoid cyclic references and leak memory!
        del frame
        del _frame
