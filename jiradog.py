#!/usr/bin/python

"""Polls JIRA API and uploads to DataDog as a metric.

Args:
    -m|--metric:	String		Specify a metric name to run from the metrics.json file.
    -l|--list:		Boolean		List metric names from metrics.json.
    -n|--noop:		Boolean		Do everything except upload to Datadog,
              				print payload to stdin.
Returns:
    On standard run, returns nothing.
"""

import argparse
import sys
import json
import time
import logging
import os
import requests
from pprint import pprint
import hashlib
import jinja2
from datadog import initialize, api
from jira import JIRA

class JiraProvider(object):
    """Group of functions/methods to get/manipulate JIRA data

    Returns:
        List of issues.
    """
    def __init__(self, api_url, api_username, api_password):
        self.jira = JIRA(api_url, basic_auth=(api_username, api_password))

    def get_issues(self, metric_data_loaded, position, project):
        """Using the JIRA SDK, gets a list of issues.

        Args:
            metric_data_loaded:	Dictionary	JSON object from the metric config block.
            position:		String		Either 'numerator' or 'denominator'.
            project:		String		The project to templatize the jql.

        Returns:
            List of issues returned from JIRA JQL query.
        """
        max_results = 100
        start_at = 100
        issues = []
        ## If/then statement failed, so I want to find  ##
        ## a way to not have to run the jinja statement ##
        ## 2 times.                                     ##
        jql_rendered = jinja2.Template(jinja2.Template(metric_data_loaded[position]['jql']).render(project=project,
                                                                                                   metric=metric_data_loaded)).render(project=project)
        jql_sha512 = hashlib.sha512(jql_rendered).hexdigest()
        if CACHE.get(jql_sha512, False):
            logging.info("Using cached version of query and results")
            issues = CACHE[jql_sha512]
        else:
            logging.info("Adding query and results to cache")
            search = self.jira.search_issues(jql_rendered, maxResults=max_results, startAt=0)
            for issue in search:
                issues.append(issue)
            while len(search) == 100:
                search = self.jira.search_issues(jql_rendered, maxResults=max_results, startAt=start_at)
                for issue in search:
                    issues.append(issue)
                start_at = start_at + max_results
            if metric_data_loaded.get(position, False).get('filter', False) != False:
                issues = self.filter_issues(metric_data_loaded, issues, position)
            CACHE[jql_sha512] = issues
        return issues

    @classmethod
    def filter_issues(cls, metric_data_loaded, issues, position):
        """Filters issues based on jinja2 format if/then statement.

        Args:
            metric_data_loaded:	Dictionary	JSON object from the metric config block.
            issues:		List		Issues returned from JIRA SDK.
            position:		String		Either 'numerator' or 'denominator'.

        Returns:
            List of issues that conform to the filter.
        """
        filtered_issues = []
        for issue in issues:
            if jinja2.Template(jinja2.Template(metric_data_loaded \
                                               [position] \
                                               ['filter']).render(issue=issue,
                                                                  metric=metric_data_loaded)).render(issue=issue) == u'true':
                filtered_issues.append(issue)
        return filtered_issues

    @classmethod
    def get_sprints(cls, metric_data_loaded, position):
        sprints = []
        max_results = 50
        start_at = max_results
        url = 'https://evernote.jira.com/rest/agile/1.0/board/' + \
              metric_data_loaded[position]['sprints']['board'] + \
              '/sprint?maxResults=' + \
              max_results
        search = requests.get(url + '&startAt=0', auth=(API_USERNAME, API_PASSWORD)).json
        sprints = search['values']
        while search['isLast'] == False:
            search = requests.get(url + '&startAt=' + start_at, auth=(API_USERNAME, API_PASSWORD)).json
            sprints.append(search['values'])
            start_at = start_at + max_results
        return sprints

def mean_time_between_statuses(first_date, second_date):
    """Calculates the length of time between two statuses

    Args:
        first_date:	String	A simple string of the start date in the format '%Y-%m-%dT%H:%M:%S'
        second_date:	String	A simple string of the end date in the format '%Y-%m-%dT%H:%M:%S'

    Returns:
        Floating point number in days
    """
    first_date_sec = time.strptime(first_date.split('.')[0], '%Y-%m-%dT%H:%M:%S')
    second_date_sec = time.strptime(second_date.split('.')[0], '%Y-%m-%dT%H:%M:%S')
    return (time.mktime(second_date_sec) - time.mktime(first_date_sec)) / (60 * 60 * 24)

## data provider methods
def custom_field_sum(issues, custom_field):
    ## Using JIRA SDK
    """Sums custom field values together.

    Args:
        issues:		List		The issue list from the JQL query
        custom_field:	String		The custom field to sum.

    Returns:
        Integer of the sum of all the found values of the custom_field.
    """
    custom_field_running_total = 0
    for issue in issues:
        if getattr(issue.fields, custom_field) is None:
            custom_field_running_total = custom_field_running_total + 2
        else:
            custom_field_running_total = custom_field_running_total + \
                                         getattr(issue.fields, custom_field)
    return custom_field_running_total

def load_metric_file(metric_file, metrics):
    """Created python dictionary from metrics.json file.

    Args:
        metric_file:		String		The file location for metrics.json.
        is_args_metric_set:	Boolean		Specifies if the entire file is to be loaded
                           			(False) or a single metric by name (True)

    Returns:
        Dictionary of the values in the metrics.json file.
    """
    with open(metric_file) as metric_file_loaded:
        metric_file_full = json.load(metric_file_loaded)
    metric_configs = metric_file_full
    if metrics:
        metric_configs = []
        for requested_metric in metrics:
            for metric in metric_file_full:
                if requested_metric == metric['metric_name']:
                    metric_configs.append(metric)  
    return metric_configs


def main():
    """Main function, calls all other functions.

    Returns:
        In a standard run, no output.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--metric',
                        metavar='METRIC',
                        action='append',
                        help='Run only the specific metric')
    parser.add_argument('-l', '--list',
                        help='Get a list of defined metrics',
                        action='store_true')
    parser.add_argument('-n', '--noop',
                        help='Outputs the payload to stdin, does not upload. Default format is JSON',
                        action='store_true')
    parser.add_argument('-f', '--formatting',
                        help='Specifies output format, default is JSON',
                        metavar='FORMATTING')
    parser.add_argument('-d', '--describe',
                        help='Prints the configuration block for the specified metric',
                        action='store_true')
    parser.add_argument('-v', '--version',
                        help='Display the version number',
                        action='store_true')

    args = parser.parse_args()

    logging.info('api configuration set')

    # Setting up DataDog SDK
    initialize(**CONFIG_DATA_LOADED['datadog'])
    logging.info('initializated datadog SDK')

    # Loads the metric configuration file
    metric_file_full = load_metric_file(METRIC_JSON, args.metric)

    if args.list:
        for metric in metric_file_full:
            print metric['metric_name']
        sys.exit(0)

    if args.describe:
        if args.metric:
            for metric in metric_file_full:
                if args.metric in metric['metric_name']:
                        pprint(metric)
        else:
            pprint(metric_file_full)
        sys.exit(0)

    if args.version:
        print os.path.basename(__file__) + ' ' + VERSION
        sys.exit(0)

    logging.info('loaded metric config')

    # Loops through list of metrics defined in a single file
    project = None
    for metric_data_loaded in metric_file_full:
        # Loop over specified projects in the metric config file.
        for project in metric_data_loaded['projects']:
            logging.info('project: ' + project)
            numbers = []
            total_time_between_statuses = 0
            if metric_data_loaded['method'] == 'average':
                ## Find the average from data providers.
                logging.info('method: ' + metric_data_loaded['method'])

                for position in ['numerator', 'denominator']:
                    if metric_data_loaded[position]['source'] == 'jira':

                        ## Get's list of issues from JIRA SDK
                        issues = JP.get_issues(metric_data_loaded, position, project)

                        if metric_data_loaded[position]['method'] == 'ticket_count':
                            numbers.append(len(issues))
                        elif metric_data_loaded[position]['method'] == 'custom_field_sum':
                            numbers.append(custom_field_sum(issues,
                                                            metric_data_loaded[position]['field']))
                        elif metric_data_loaded[position]['method'] == 'mean_time_between_statuses':
                            for issue in issues:
                                first_date = jinja2.Template(metric_data_loaded \
                                                             [position] \
                                                             ['statuses'] \
                                                             [0]).render(issue=issue)
                                second_date = jinja2.Template(metric_data_loaded \
                                                             [position] \
                                                             ['statuses'] \
                                                             [1]).render(issue=issue)
                                m_t = mean_time_between_statuses(first_date,
                                                                 second_date)
                                total_time_between_statuses = total_time_between_statuses + m_t
                            numbers.append(total_time_between_statuses)
                    elif metric_data_loaded[position]['source'] == 'constant':
                        numbers.append(metric_data_loaded[position]['data'][project])

                    if len(numbers) == 2:
                        if float(numbers[1]) != 0:
                            points = float(numbers[0]) / float(numbers[1])
                        else:
                            points = 0

            elif metric_data_loaded['method'] == 'direct':
                issues = JP.get_issues(metric_data_loaded, 'issues', project)
                if metric_data_loaded['issues']['method'] == 'ticket_count':
                    points = len(issues)

        ## Construct payload for upload
            metric_data = {
                'metric': metric_data_loaded['metric_name'],
                'points': (NOW, points),
                'tags': ["jira_project:%s" % project]
                }
            PAYLOAD.append(metric_data)

    logging.info('payload: ' + str(PAYLOAD))

    if args.noop:
        if not args.formatting or args.formatting == 'json':
            pprint(PAYLOAD)
        elif args.formatting == 'jira' or args.formatting == 'markdown':
            if args.formatting == 'jira':
                print '||metric||project||points||'
            elif args.formatting == 'markdown':
                print '|metric|project|points|'
                print '| ----- | ----- | ----- |'
            for payload in PAYLOAD:
                print '|' + payload['metric'] + '|' + payload['tags'][0] + '|' + str(payload['points'][1]) + '|'
    else:
        # Upload to DataDog
        api.Metric.send(PAYLOAD)
        logging.info('uploaded to DataDog')

if __name__ == "__main__":
    # Setting important variables, all static.
    VERSION = '1.1.2'
    FUNCTION_MAP = {
        'mean_time_between_statuses': mean_time_between_statuses,
        'custom_field_sum': custom_field_sum
        }
    MAX_RESULTS = str(100)
    CONFIG_FILE = 'config.json'
    HEADERS = {'Content-type': 'application/json'}
    CACHE = {}
    PAYLOAD = []
    NOW = time.time()

    # Loads the configuration file for the script.
    with open(CONFIG_FILE) as config_data_file:
        CONFIG_DATA_LOADED = json.load(config_data_file)

    # Set important information scraped from the configuration file.
    API_USERNAME = CONFIG_DATA_LOADED['jira']['username']
    API_PASSWORD = CONFIG_DATA_LOADED['jira']['password']
    API_URL = CONFIG_DATA_LOADED['jira']['server']
    API_ENDPOINT = API_URL + '/rest/api/2/search?jql='
    LOG_FILE = CONFIG_DATA_LOADED['local']['log_file']
    METRIC_JSON = CONFIG_DATA_LOADED['local']['metric_file']

    # Set logging config
    LOGGING_LEVELS = {
        'info': logging.INFO,
        'debug': logging.DEBUG,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
        }
    LOGGING_LEVEL = LOGGING_LEVELS.get('debug', logging.NOTSET)
    logging.basicConfig(filename=LOG_FILE,
                        format='%(asctime)s %(levelname)s %(message)s',
                        level=LOGGING_LEVEL)
    JP = JiraProvider(API_URL, API_USERNAME, API_PASSWORD)

    # Executing script
    main()
