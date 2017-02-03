import unittest
try:
    from unittest import mock
except:
    import mock

import tm
import Args

class TestArgs(unittest.TestCase):
    def test_args(self):
        args = Args.Args(['--timeout=10'])
        self.assertIn('timeout', args.args)
        self.assertEqual(args.args['timeout'], '10')

class TestTM(unittest.TestCase):
    def test_parse_global_config(self):
        args = Args.Args(['--timeout=10'])
        tm.parse_global_config(args.args)
        self.assertEqual(tm.tm_timeout, 10)

if __name__ == '__main__':
    unittest.main()
