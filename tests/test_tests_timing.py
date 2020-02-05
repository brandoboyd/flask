"""
Tests for scripts/tests_timing.py
"""

import unittest 

from solariat_bottle.scripts.tests_timing import get_file_test_time

# this needs to be set so that nose does not think it is a test
get_file_test_time.__test__ = False


class TestTestsTime(unittest.TestCase):

    def test_get_file_test_time(self):
        """Tests ``get_file_test_time`` function.
        """
        correct_file_name = "test_demo_data"
        correct_test_name = "DemoDataScriptCase.test_demo_data_script"
        correct_time_str = "23.4872"
        line = "solariat_bottle.tests." + \
               "{file_name}.{test_name}: {test_time}s".format(
                    file_name=correct_file_name,
                    test_name=correct_test_name,
                    test_time=correct_time_str)
        file_name, test_name, test_time = get_file_test_time(line)
        self.assertEqual(file_name, correct_file_name)
        self.assertEqual(test_name, correct_test_name)
        self.assertAlmostEqual(test_time, float(correct_time_str), 4)

    def test_get_file_test_time_not_test(self):
        line = "<nose.suite.ContextSuite context=TestFacebookPullModel>" + \
               ":teardown: 0.0707s"
        self.assertEqual(get_file_test_time(line), (None, None, None))

    def test_get_file_test_time_empty(self):
        """Tests ``get_file_test_time`` function with empty line.
        """
        line = "   "
        self.assertEqual(get_file_test_time(line), (None, None, None))

    def test_get_file_test_time_wrong(self):
        """Tests ``get_file_test_time`` with wrong parameter.
        """
        line = 'some wrong line without time'
        self.assertRaises(ValueError, get_file_test_time, line)
