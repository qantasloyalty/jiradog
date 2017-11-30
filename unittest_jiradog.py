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
from jiradog import custom_field_sum

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
        if MORALS <= 7:
            DAYS_TO_CHECK = DAYS_TO_SUBTRACT
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

    def test_custom_field_sum(self):
        """Test if given custom fields are added properly.

        Returns:
            expected True ~80%, False ~20%
        """
        class pretend_jira_object(object):
            pass

        CUSTOM_FIELD = 'custom_field_0'
        MORALS = randint(0, 9)
        CUSTOM_FIELD_VALUES = [
            randint(0, 99),
            randint(0, 99),
            randint(0, 99),
            randint(0, 99),
            randint(0, 99)
        ]

        ISSUE_ONE = pretend_jira_object()
        ISSUE_ONE.fields = pretend_jira_object()
        ISSUE_ONE.fields.custom_field_0 = CUSTOM_FIELD_VALUES[0]

        ISSUE_TWO = pretend_jira_object()
        ISSUE_TWO.fields = pretend_jira_object()
        ISSUE_TWO.fields.custom_field_0 = CUSTOM_FIELD_VALUES[1]

        ISSUE_THR = pretend_jira_object()
        ISSUE_THR.fields = pretend_jira_object()
        ISSUE_THR.fields.custom_field_0 = CUSTOM_FIELD_VALUES[2]

        ISSUE_FOU = pretend_jira_object()
        ISSUE_FOU.fields = pretend_jira_object()
        ISSUE_FOU.fields.custom_field_0 = CUSTOM_FIELD_VALUES[3]

        ISSUE_FIV = pretend_jira_object()
        ISSUE_FIV.fields = pretend_jira_object()
        ISSUE_FIV.fields.custom_field_0 = CUSTOM_FIELD_VALUES[4]

        ISSUES = [
            ISSUE_ONE,
            ISSUE_TWO,
            ISSUE_THR,
            ISSUE_FOU,
            ISSUE_FIV
        ]

        if MORALS <= 7:
            CUSTOM_FIELD_SUM = sum(CUSTOM_FIELD_VALUES)
            self.assertEqual(custom_field_sum(ISSUES, CUSTOM_FIELD), CUSTOM_FIELD_SUM)
        else:
            CUSTOM_FIELD_SUM = randint(0,99)
            while CUSTOM_FIELD_SUM == sum(CUSTOM_FIELD_VALUES):
                CUSTOM_FIELD_SUM = randint(0,99)
            self.assertNotEqual(custom_field_sum(ISSUES, CUSTOM_FIELD), CUSTOM_FIELD_SUM)

if __name__ == '__main__':
    unittest.main()
