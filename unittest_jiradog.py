#!/usr/bin/python
"""Unit tests for jiradog.py"""

import unittest
import json
import time
import datetime
from random import randint
from jiradog import mean_time_between_statuses
from jiradog import load_metric_file
from jiradog import pretty_date

class JiradogTestCase(unittest.TestCase):
    """Testing for `jiradog.py`"""

    def test_pretty_date(self):
        """Test if pretty_date returns a timestruct and if it's accurate.

        Returns:
            expected True
        """
        DATE = '1993-11-22T03:04:05.000'
        self.assertEqual(pretty_date(DATE), time.strptime(DATE.split('.')[0], '%Y-%m-%dT%H:%M:%S'))

    def test_mean_time_between_statuses(self):
        """Test if 2 given dates are N days apart.

        Returns:
            expected True ~80%, False ~20%
        """
        MORALS = randint(0, 9)
        DAYS_TO_SUBTRACT = randint(1, 50)
        NOW_DATE_TIME = datetime.datetime.now()
        NOW = datetime.date.strftime(NOW_DATE_TIME,
                                     '%Y-%m-%dT%H:%M:%S.000')
        THEN = datetime.date.strftime(NOW_DATE_TIME - datetime.timedelta(days=DAYS_TO_SUBTRACT),
                                      '%Y-%m-%dT%H:%M:%S.000')
        METRIC_DATA_LOADED = {
            'numerator': {
                'statuses': [
                    '{{issue.fields.created}}',
                    '{{issue.fields.updated}}'
                    ]
                }
            }
        POSITION = 'numerator'
        ISSUE = {
        'fields': {
            'created': THEN,
            'updated': NOW
            }
        }
        if MORALS < 7:
            DAYS_TO_CHECK = DAYS_TO_SUBTRACT
            print mean_time_between_statuses(METRIC_DATA_LOADED, POSITION, ISSUE)
            self.assertEqual(mean_time_between_statuses(METRIC_DATA_LOADED, POSITION, ISSUE),
                             DAYS_TO_CHECK)
        else:
            DAYS_TO_CHECK = randint(1, 50)
            while DAYS_TO_CHECK == DAYS_TO_SUBTRACT:
                DAYS_TO_CHECK = randint(1, 50)
            self.assertNotEqual(mean_time_between_statuses(METRIC_DATA_LOADED, POSITION, ISSUE),
                                DAYS_TO_CHECK)

    def test_load_metric_file(self):
        """Test if given json loads.

        Returns:
            expected True
        """
        CONFIG_FILE = '/etc/jiradog/config.json'
        with open(CONFIG_FILE) as config_data_file:
            CONFIG_DATA_LOADED = json.load(config_data_file)
        METRIC_FILE = CONFIG_DATA_LOADED['local']['metric_file']
        with open(METRIC_FILE) as metric_data_file:
            METRIC_DATA_LOADED = json.load(metric_data_file)
        self.assertEqual(load_metric_file(METRIC_FILE, False), METRIC_DATA_LOADED)

if __name__ == '__main__':
    unittest.main()
