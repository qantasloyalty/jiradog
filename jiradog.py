#!/usr/bin/python

import sys
import requests
import json
import io
import urllib
import re
from datadog import initialize, api
from pprint import pprint
import time
from jira import JIRA
import argparse

class jira_provider(object):
  def __init__(self, username, password, server):
    self.jira = JIRA(server, basic_auth=(username, password))

  def paginate(self, base_api_url, total, max_results):
    pages = (total / int(max_results)) + 1
    paginations = []
    for start_at in range(0, pages):
      paginations.append(base_api_url + '&startAt=' + str(start_at * int(max_results)))
    return paginations

  def provide(self, provider_config, project, max_results, log_prepend):
    jql_raw_regex = re.sub(r"{{project}}", project, provider_config["jql"])
    jql_url_encoded = urllib.quote(jql_raw_regex)
    jira_api_call_url = api_endpoint + jql_url_encoded + '&maxResults=' + max_results
    jira_api_response = json.loads(requests.get(jira_api_call_url, headers=headers, auth=(api_username, api_password)).text)
    jira_api_responses = []
    for url in self.paginate(jira_api_call_url, jira_api_response['total'], max_results):
      jira_api_response = requests.get(url, headers=headers, auth=(api_username, api_password))
      if jira_api_response.status_code == 200:
        print log_prepend + ' Running API call; URL: ' + url
        print log_prepend + ' API response: ' + str(jira_api_response.status_code)
        jira_api_responses.append(json.loads(jira_api_response.text))
      else:
        print re.sub(r"[INFO]", "[WARN]", log prepend) + ' Did not recieve an HTTP status code of 200 in response to the API request. Retrying...'
        time.sleep(10)
        jira_api_response = requests.get(url, headers=headers, auth=(api_username, api_password))
        if jira_api_responses.status_code == 200:
          print log_prepend + ' Running API call; URL: ' + url
          print log_prepend + ' API response: ' + str(jira_api_response.status_code)
        else:
          print re.sub(r"[INFO]", "[ERROR]", log_prepend) + ' API URL(' + url + ') result not added to list because status code was not 200'
    return jira_api_responses

class constant_provider(object):
  def provide(self, data, project):
    return data["data"][project]

def average(avg_numerator, avg_denominator):
  return float(avg_numerator)/float(avg_denominator)

def mean_time_to_between_statuses(first_date, second_date):
  first_date_sec = time.strptime(first_date.split('.')[0],'%Y-%m-%dT%H:%M:%S')
  second_date_sec = time.strptime(second_date.split('.')[0],'%Y-%m-%dT%H:%M:%S')
  return (time.mktime(second_date_sec) - time.mktime(first_date_sec)) / 60 / 60 / 24

def ticket_count(result, null_field):
  return len(result['issues'])

def custom_field_sum(result, custom_field):
  custom_field_values = []
  for issue in result['issues']:
    if issue['fields'][custom_field] is None:
      custom_field_values.append(2)
    else:
      custom_field_values.append(issue['fields'][custom_field])
  return sum(custom_field_values)

function_map = {
  'average': average,
  'mean_time_to_between_statuses': mean_time_to_between_statuses,
  'ticket_count': ticket_count,
  'custom_field_sum': custom_field_sum
}
max_results = str(100)
config_file = '/etc/jiradog.conf'

with open(config_file) as config_data_file:
  config_data_loaded = json.load(config_data_file)

api_username = config_data_loaded['jira']['username']
api_password = config_data_loaded['jira']['password']
api_url = config_data_loaded['jira']['server']
api_endpoint = api_url + '/rest/api/2/search?jql='
log_prepend = '[INFO]'
print log_prepend + ' api configurations set'

print log_prepend + ' initializing datadog SDK...'
initialize(**config_data_loaded['datadog'])
print log_prepend + ' initialized datadog SDK'

for metric_file in sys.argv[1:]:
  headers = {'Content-type': 'application/json'}
  upload_payload = {}

  with open(metric_file) as metric_data_file:
    metric_data_loaded = json.load(metric_data_file)

  metric_file_method = metric_data_loaded['method']
  datadog_metric_name = metric_data_loaded['metric_name']
  log_prepend = log_prepend + '[' + datadog_metric_name + ']'
  print log_prepend + ' loaded metric file'

  jp = jira_provider(api_username, api_password, api_url)
  cp = constant_provider()

  timestamp = time.time()
  upload_payload = []

  # JIRA api call
  for project in metric_data_loaded['projects']:
    log_prepend = '[INFO][' +  datadog_metric_name + ']'
    print log_prepend + ' project: ' + project
    log_prepend = log_prepend + '[' + project + ']'
    ## Method: Average
    if metric_data_loaded['method'] == 'average':
      print log_prepend + ' method: ' + metric_data_loaded['method']
      log_prepend = log_prepend + '[' + metric_data_loaded['method'] + ']'

      if metric_data_loaded['avg_numerator']['source'] == 'jira':
        print log_prepend + ' numerator data provider: ' + metric_data_loaded['avg_numerator']['source']
        log_prepend_numerator = log_prepend + '[' + metric_data_loaded['avg_numerator']['source'] + ']'
        paginated_list = jp.provide(metric_data_loaded['avg_numerator'], project, max_results, log_prepend)
        running_total = []
        for result in paginated_list:
          running_total.append(function_map[metric_data_loaded['avg_numerator']['method']](result, metric_data_loaded['avg_numerator']['field']))
        avg_numerator = sum(running_total)
        print log_prepend_numerator + 'numerator: ' + str(avg_numerator)
      elif metric_data_loaded['avg_numerator']['source'] == 'constant':
        print log_prepend_numerator + 'numerator data provider: ' + metric_data_loaded['avg_numerator']['source']
        log_prepend = log_prepend + '[' + metric_data_loaded['avg_numerator']['source'] + '] '
        avg_numerator = cp.provide(metric_data_loaded["avg_numerator"], project)
        print log_prepend_numerator + 'numerator: ' + str(avg_numerator)
      else:
        print "[ERROR]: avg_numerator source is set to an unknown value: %s" % metric_data_loaded['avg_numerator']['source']
        quit()

      if metric_data_loaded['avg_denominator']['source'] == 'jira':
        print log_prepend + 'denominator data provider: ' + metric_data_loaded['avg_denominator']['source']
        log_prepend_denominator = log_prepend + '[' + metric_data_loaded['avg_denominator']['source'] + ']'
        paginated_list = jp.provide(metric_data_loaded['avg_denominator'], project, max_results, log_prepend)
        running_total = []
        for result in paginated_list:
          running_total.append(function_map[metric_data_loaded['avg_denominator']['method']](result, metric_data_loaded['avg_denominator']['field']))
        avg_denominator = sum(running_total)
        print log_prepend_denominator + ' denominator: ' + str(avg_denominator)
      elif metric_data_loaded['avg_denominator']['source'] == 'constant':
        print log_prepend_denominator + ' denominator data provider: ' + metric_data_loaded['avg_denominator']['source']
        log_prepend_denominator = log_prepend + '[' + metric_data_loaded['avg_denominator']['source'] + ']'
        avg_denominator = cp.provide(metric_data_loaded["avg_denominator"], project)
        print log_prepend_denominator + ' denominator: ' + str(avg_denominator)
      else:
        print "[ERROR]: avg_denominator source is set to an unknown value: %s" % metric_data_loaded['avg_denominator']['source']
        quit()
  
      points = function_map[metric_file_method](avg_numerator, avg_denominator)

    ## Method: mean time between statuses
    if metric_data_loaded['method'] == 'mean_time_to_between_statuses':
      print log_prepend + ' method: ' + metric_data_loaded['method']
      log_prepend = log_prepend + '[' + metric_data_loaded['method'] + ']'
      status_start_dates = []
      status_end_dates = []
      status_dates = {}
      paginated_list = jp.provide(metric_data_loaded['issues'], project, max_results, log_prepend)
      for status_start in paginated_list:
        for issue_fields in status_start['issues']:
          status_start_dates.append(issue_fields['fields']['created'])
          status_end_dates.append(issue_fields['fields']['updated'])
          status_dates[issue_fields['fields']['created']] = issue_fields['fields']['updated']

     #  status_dates = dict(zip(status_start_dates, status_end_dates))
      denominator = paginated_list[0]['total']

      date_diff_days = []
      for date in status_dates:
        date_diff_days.append(mean_time_to_between_statuses(date, status_dates[date]))

      if denominator != 0:
        points = average(sum(date_diff_days), denominator)
      else:
        points = 0

    ## Construct payload for upload
    metric_data = {
      'metric': datadog_metric_name,
      'points': (timestamp, points),
      'tags': ["jira_project:%s" % project]
      }
    upload_payload.append(metric_data) 

  print '[INFO][' + datadog_metric_name + '][' + project + '] payload: '
  print upload_payload

  # Upload to DataDog
  result = api.Metric.send(upload_payload)
  print '[INFO][' + datadog_metric_name + '] uploaded to DataDog.'
