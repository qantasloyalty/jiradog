#!/usr/bin/python
"""Unit tests for jiradog.py"""

import unittest
import json
import time
import datetime
import random
from jiradog import mean_time_between_statuses
from jiradog import load_metric_file
from jiradog import pretty_date
from jiradog import custom_field_sum
from jiradog import JiraProvider

class JiradogTestCase(unittest.TestCase):
    """Testing for `jiradog.py`"""

    def test_pretty_date(self):
        """Test if pretty_date returns a timestruct and if it's accurate.

        Returns:
            expected True
        """
        date = '1993-11-22T03:04:05.000'
        self.assertEqual(pretty_date(date), time.strptime(date.split('.')[0], '%Y-%m-%dT%H:%M:%S'))

    def test_mean_time_between_statuses(self):
        """Test if 2 given dates are N days apart.

        Returns:
            expected True ~80%, False ~20%
        """
        morals = random.randint(0, 9)
        days_to_subtract = random.randint(1, 50)
        now_date_time = datetime.datetime.now()
        now = datetime.date.strftime(now_date_time,
                                     '%Y-%m-%dT%H:%M:%S.000')
        then = datetime.date.strftime(now_date_time - datetime.timedelta(days=days_to_subtract),
                                      '%Y-%m-%dT%H:%M:%S.000')
        metric_data_loaded = {
            'numerator': {
                'statuses': [
                    '{{issue.fields.created}}',
                    '{{issue.fields.updated}}'
                    ]
                }
            }
        position = 'numerator'
        issue = {
            'fields': {
                'created': then,
                'updated': now
            }
        }
        if morals <= 7:
            days_to_check = days_to_subtract
            self.assertEqual(mean_time_between_statuses(metric_data_loaded, position, issue),
                             days_to_check)
        else:
            days_to_check = random.randint(1, 50)
            while days_to_check == days_to_subtract:
                days_to_check = random.randint(1, 50)
            self.assertNotEqual(mean_time_between_statuses(metric_data_loaded, position, issue),
                                days_to_check)

    def test_load_metric_file(self):
        """Test if given json loads.

        Returns:
            expected True
        """
        config_file = '/etc/jiradog/config.json'
        with open(config_file) as config_data_file:
            config_data_loaded = json.load(config_data_file)
        metric_file = config_data_loaded['local']['metric_file']
        with open(metric_file) as metric_data_file:
            metric_data_loaded = json.load(metric_data_file)
        self.assertEqual(load_metric_file(metric_file, False), metric_data_loaded)

    def test_custom_field_sum(self):
        """Test if given custom fields are added properly.

        Returns:
            expected True ~80%, False ~20%
        """
        class PretendJiraObject(object): #pylint: disable=R0903
            """Fake object, used to imitate the return from the JIRA SDK."""
            def __init__(self):
                """Defining fake attributes"""
                self.fields = None
                self.custom_field_0 = None

        custom_field = 'custom_field_0'
        morals = random.randint(0, 9)
        custom_field_values = [
            random.randint(0, 99),
            random.randint(0, 99),
            random.randint(0, 99),
            random.randint(0, 99),
            random.randint(0, 99)
        ]

        issue_one = PretendJiraObject()
        issue_one.fields = PretendJiraObject()
        issue_one.fields.custom_field_0 = custom_field_values[0]

        issue_two = PretendJiraObject()
        issue_two.fields = PretendJiraObject()
        issue_two.fields.custom_field_0 = custom_field_values[1]

        issue_thr = PretendJiraObject()
        issue_thr.fields = PretendJiraObject()
        issue_thr.fields.custom_field_0 = custom_field_values[2]

        issue_fou = PretendJiraObject()
        issue_fou.fields = PretendJiraObject()
        issue_fou.fields.custom_field_0 = custom_field_values[3]

        issue_fiv = PretendJiraObject()
        issue_fiv.fields = PretendJiraObject()
        issue_fiv.fields.custom_field_0 = custom_field_values[4]

        issues = [
            issue_one,
            issue_two,
            issue_thr,
            issue_fou,
            issue_fiv
        ]

        if morals <= 7:
            custom_fields_sum = sum(custom_field_values)
            self.assertEqual(custom_field_sum(issues, custom_field), custom_fields_sum)
        else:
            custom_fields_sum = random.randint(0, 99)
            while custom_fields_sum == sum(custom_field_values):
                custom_fields_sum = random.randint(0, 99)
            self.assertNotEqual(custom_field_sum(issues, custom_field), custom_fields_sum)

    def test_jira_filter_issues(self):
        """Test if given filter properly filters the correct issues

        Returns:
            expected True
        """
        class PretendJiraObject(object): #pylint: disable=R0903
            """Fake object, used to imitate the return from the JIRA SDK."""
            def __init__(self):
                """Define fake attributes"""
                self.fields = None
                self.fixVersions = None #pylint: disable=C0103
                self.name = None

        morals = random.randint(0, 9)
        all_fixversions = [
            'faint',
            'replace',
            'rare',
        ]

        fixversions = [
            random.choice(all_fixversions),
            random.choice(all_fixversions),
            random.choice(all_fixversions),
            random.choice(all_fixversions),
            random.choice(all_fixversions)
        ]
        fixversion = random.choice(fixversions)
        count = fixversions.count(fixversion)
        jinja2_filter = {
            "only": {
                "filter": "{% if '" + \
                          fixversion + \
                          "' in issue.fields.fixVersions[0].name %}true{% endif %}"
            }
        }

        issue_one = PretendJiraObject()
        issue_one.fields = PretendJiraObject()
        issue_one.fields.fixVersions = [PretendJiraObject()] #pylint: disable=C0103
        issue_one.fields.fixVersions[0].name = fixversions[0]

        issue_two = PretendJiraObject()
        issue_two.fields = PretendJiraObject()
        issue_two.fields.fixVersions = [PretendJiraObject()]
        issue_two.fields.fixVersions[0].name = fixversions[1]

        issue_thr = PretendJiraObject()
        issue_thr.fields = PretendJiraObject()
        issue_thr.fields.fixVersions = [PretendJiraObject()]
        issue_thr.fields.fixVersions[0].name = fixversions[2]

        issue_fou = PretendJiraObject()
        issue_fou.fields = PretendJiraObject()
        issue_fou.fields.fixVersions = [PretendJiraObject()]
        issue_fou.fields.fixVersions[0].name = fixversions[3]

        issue_fiv = PretendJiraObject()
        issue_fiv.fields = PretendJiraObject()
        issue_fiv.fields.fixVersions = [PretendJiraObject()]
        issue_fiv.fields.fixVersions[0].name = fixversions[4]

        issues = [
            issue_one,
            issue_two,
            issue_thr,
            issue_fou,
            issue_fiv
        ]

        if morals <= 7:
            self.assertEqual(len(JiraProvider.filter_issues(jinja2_filter, issues, "only")), count)
        else:
            wrong_count = random.randint(0, 99)
            while wrong_count == count:
                wrong_count = random.randint(0, 99)
            self.assertNotEqual(len(JiraProvider.filter_issues(jinja2_filter,
                                                               issues,
                                                               "only")),
                                wrong_count)

if __name__ == '__main__':
    unittest.main()
