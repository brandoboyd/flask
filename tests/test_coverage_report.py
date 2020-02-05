"""
Tests for coverage report
"""

from mock import patch, MagicMock
from unittest import TestCase

from solariat_bottle.scripts.coverage_get_data import (
    get_commit_hash)


class TestCoverageReport(TestCase):

    @patch('solariat_bottle.scripts.coverage_get_data.subprocess.Popen')
    def test_get_commit_hash(self, Popen):
        """Test that commit hash is obtained.
        """
        mock = MagicMock()
        mock.communicate.return_value = ('commithash - commit description', None)
        Popen.return_value = mock
        self.assertEqual('commithash', get_commit_hash('m_zero'))
