#!/usr/bin/python

import unittest
import json
from jiradog import mean_time_between_statuses
from jiradog import load_metric_file

class JiradogTestCase(unittest.TestCase):
    """Testing for `jiradog.py`"""

    def test_mean_time_between_statuses(self):
        """Test if 2 given dates are 5 days apart

        Returns:
            expected True
        """
        self.assertEqual(mean_time_between_statuses('2017-10-25T12:00:00', '2017-10-30T12:00:00'), 5)

    def test_load_metric_file(self):
        """Test if diven json loads

        Returns:
            expected True
        """
        CONFIG_FILE = 'config.json'
        with open(CONFIG_FILE) as config_data_file:
            CONFIG_DATA_LOADED = json.load(config_data_file)
        METRIC_FILE = CONFIG_DATA_LOADED['local']['metric_file']
        with open(METRIC_FILE) as metric_data_file:
            METRIC_DATA_LOADED = json.load(metric_data_file)
        self.assertEqual(load_metric_file(METRIC_FILE, True), METRIC_DATA_LOADED)

if __name__ == '__main__':
    unittest.main()
