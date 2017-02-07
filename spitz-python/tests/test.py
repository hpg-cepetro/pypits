import time
import unittest
try:
    from unittest import mock
except:
    import mock

import tm
import Args
from libspitz import timeout

class TestArgs(unittest.TestCase):
    def test_args(self):
        args = Args.Args(['--timeout=10', 'module', 'arg1', 'arg2'])
        self.assertIn('timeout', args.args)
        self.assertEqual(args.args['timeout'], '10')
        self.assertSequenceEqual(['module', 'arg1', 'arg2'], args.margs)

class TestTM(unittest.TestCase):
    def test_parse_global_config(self):
        args = Args.Args(['--timeout=10'])
        tm.parse_global_config(args.args)
        self.assertEqual(tm.tm_timeout, 10)


class TestTimeout(unittest.TestCase):
    def setUp(self):
        def callback(x):
            x['foo'] += 1
        self.x = {'foo': 0}
        self.cb = callback

    def test_timeout_noop(self):
        timeout(0, self.cb, args=[self.x]).reset()
        timeout(-1, self.cb, args=[self.x]).reset()
        timeout(None, self.cb, args=[self.x]).reset()
        self.assertEqual(self.x['foo'], 0)

    def test_timeout(self):
        t = timeout(0.2, self.cb, args=[self.x])
        for i in range(3):
            t.reset()
            time.sleep(0.1)
        time.sleep(0.5)
        self.assertEqual(self.x['foo'], 1)

    def test_timeout_cancel(self):
        t = timeout(0.1, self.cb, args=[self.x])
        t.reset()
        t.cancel()
        time.sleep(0.5)
        self.assertEqual(self.x['foo'], 0)

if __name__ == '__main__':
    unittest.main()
