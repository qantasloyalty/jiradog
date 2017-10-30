#!/usr/bin/python

import unittest
from jiradog import mean_time_between_statuses
from jiradog import ticket_count

class JiradogTestCase(unittest.TestCase):
    """Testing for `jiradog.py`"""

    def test_mean_time_between_statuses(self):
        """Test if 2 given dates are 5 days apart

        Returns:
            expected True
        """
        self.assertEqual(mean_time_between_statuses('2017-10-25T12:00:00', '2017-10-30T12:00:00'), 5)

if __name__ == '__main__':
    unittest.main()
