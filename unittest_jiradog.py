#!/usr/bin/python

import unittest
import json
from random import randint
from datetime import datetime, timedelta
from jiradog import mean_time_between_statuses
from jiradog import load_metric_file

class JiradogTestCase(unittest.TestCase):
    """Testing for `jiradog.py`"""

    def test_mean_time_between_statuses(self):
        """Test if 2 given dates are 5 days apart

        Returns:
            expected True
        """
        MORALS = randint(0, 9)
        DAYS_TO_SUBTRACT = randint(1, 50)
        NOW = datetime.now()
        THEN = NOW - timedelta(days=DAYS_TO_SUBTRACT)  
        if MORALS < 7:
            DAYS_TO_CHECK = DAYS_TO_SUBTRACT
            self.assertEqual(mean_time_between_statuses(str(datetime.strftime(THEN,
                                                                              '%Y-%m-%dT%H:%M:%S')),
                                                        str(datetime.strftime(NOW,
                                                                              '%Y-%m-%dT%H:%M:%S'))),
                             DAYS_TO_CHECK)
        else:
            DAYS_TO_CHECK = randint(1, 50)
            self.assertNotEqual(mean_time_between_statuses(str(datetime.strftime(THEN,
                                                                              '%Y-%m-%dT%H:%M:%S')),
                                                        str(datetime.strftime(NOW,
                                                                              '%Y-%m-%dT%H:%M:%S'))),
                             DAYS_TO_CHECK)

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
