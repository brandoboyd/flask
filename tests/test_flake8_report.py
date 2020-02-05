"""
These tests check that analysis of flake8 output works correctly.
"""

import os
from unittest import TestCase

from ..scripts.flake8_generate_report import (
    get_warnings_counts, get_top_warnings,
    get_github_link, get_warning_messages)


class TestFlakeReport(TestCase):

    def test_total(self):
        """
        Tests that total number of warnings is calculated correctly.
        """
        warnings_counts_dict, warnings_messages_dict = get_warnings_counts(
            os.path.join(os.path.dirname(__file__), 'flake8/flake_out.txt'))
        total = sum(warnings_counts_dict.values())
        self.assertEqual(total, 95)
        self.assertEqual(len(warnings_counts_dict), len(warnings_messages_dict))
        for k in warnings_messages_dict:
            self.assertIn(k, warnings_counts_dict)

    def test_top_warnings(self):
        """
        Tests that tops warnings are calcuated correctly.
        """
        warnings_counts_dict, warnings_messages_dict = get_warnings_counts(
            os.path.join(os.path.dirname(__file__), 'flake8/flake_out.txt'))
        top_warnings = get_top_warnings(warnings_counts_dict, 10)
        self.assertEqual(top_warnings[0][0], 'E201')
        self.assertEqual(top_warnings[0][1], 6)
        for warning in top_warnings[1:]:
            self.assertEqual(warning[1], 5)

    def test_link_to_github(self):
        """
        Tests function that generates link to Github
        """
        warning1 = "./tests/test_tracking.py:364:25: E201 whitespace after '('"  # noqa
        warning2 = "./tests/aggregation.py:100: W806 local variable 'doc_2' is assigned to but never used"  # noqa
        url1 = "https://github.com/solariat/tango/blob/m_zero/solariat_bottle/src/solariat_bottle/tests/test_tracking.py#L364"  # noqa
        url2 = "https://github.com/solariat/tango/blob/m_zero/solariat_bottle/src/solariat_bottle/tests/aggregation.py#L100"  # noqa
        self.assertEqual(get_github_link(warning1), url1)
        self.assertEqual(get_github_link(warning2), url2)

    def test_ignore_warnings(self):
        """
        Tests that options can be set to ignore some warnings in analysis
        """
        warnings_counts_dict, warnings_messages_dict = get_warnings_counts(
            os.path.join(os.path.dirname(__file__), 'flake8/flake_out.txt'),
            ignore_warnings=['E202'])
        total = sum(warnings_counts_dict.values())
        self.assertEqual(total, 90)
        self.assertFalse('E202' in warnings_counts_dict)
        self.assertTrue('E201' in warnings_counts_dict)

    def test_get_warning_occurance(self):
        """
        Tests that first warning occurance is obtained correctly
        """
        warnings = ['E201', 'E202', 'W292']
        expected_messages = [
            "./tests/test_tracking.py:364:25: E201 whitespace after '('",
            "./tests/test_tracking.py:364:86: E202 whitespace before ')'",
            "./__init__.py:5:11: W292 no newline at end of file",
        ]
        obtained_messages = get_warning_messages(
            os.path.join(os.path.dirname(__file__), 'flake8/flake_out.txt'),
            warnings
        )
        self.assertEqual(len(expected_messages), len(obtained_messages))
        for m in obtained_messages:
            self.assertIn(m, expected_messages)
