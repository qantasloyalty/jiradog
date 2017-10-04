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

  def provide(self, provider_config, project):
    jql_raw_regex = re.sub(r"{{project}}", project, provider_config["jql"])
    jql_url_encoded = urllib.quote(jql_raw_regex)
    jira_api_call_url = api_endpoint + jql_url_encoded + "&maxResults=100"
    jira_api_response = json.loads(requests.get(jira_api_call_url, headers=headers, auth=(api_username, api_password)).text)
    return jira_api_response

class constant_provider(object):
  def provide(self, data, project):
    return data["data"][project]

def average(avg_numerator, avg_denominator):
  return float(avg_numerator)/float(avg_denominator)

def mean_time_to_between_statuses(first_date, second_date):
  first_date_sec = time.strptime(first_date.split('.')[0],'%Y-%m-%dT%H:%M:%S')
  second_date_sec = time.strptime(second_date.split('.')[0],'%Y-%m-%dT%H:%M:%S')
  return (time.mktime(second_date_sec) - time.mktime(first_date_sec)) / 60 / 60 / 24
  
function_map = {
  'average': average,
  'mean_time_to_between_statuses': mean_time_to_between_statuses
}

config_file = '/etc/jiradog.conf'

with open(config_file) as config_data_file:
  config_data_loaded = json.load(config_data_file)

api_username = config_data_loaded['jira']['username']
api_password = config_data_loaded['jira']['password']
api_url = config_data_loaded['jira']['server']
api_endpoint = api_url + '/rest/api/2/search?jql='
print '[INFO] api configurations set'

for metric_file in sys.argv[1:]:
  print '[INFO] loading metric file: ' + metric_file
  headers = {'Content-type': 'application/json'}
  upload_payload = {}

  print '[INFO] initializing datadog SDK...'
  initialize(**config_data_loaded['datadog'])
  print '[INFO]: initialized datadog SDK'

  with open(metric_file) as metric_data_file:
    metric_data_loaded = json.load(metric_data_file)

  metric_file_method = metric_data_loaded['method']
  datadog_metric_name = metric_data_loaded['metric_name']
  print '[INFO][' + datadog_metric_name + '] loaded metric file'

  jp = jira_provider(api_username, api_password, api_url)
  cp = constant_provider()

  timestamp = time.time()
  upload_payload = []

  # JIRA api call
  print '[INFO][' + datadog_metric_name + '] starting API poll...'
  for project in metric_data_loaded['projects']:
    print '[INFO][' + datadog_metric_name + '] project: ' + project
    ## Method: Average
    if metric_data_loaded['method'] == 'average':
      print '[INFO][' + datadog_metric_name + '][' + project + '] method: ' + metric_data_loaded['method']

      if metric_data_loaded['avg_numerator']['source'] == 'jira':
        print '[INFO][' + datadog_metric_name + '][' + project + '][' + metric_data_loaded['method'] + '] numerator data provider: ' + metric_data_loaded['avg_numerator']['source']
        avg_numerator_raw = jp.provide(metric_data_loaded["avg_numerator"], project)
        avg_numerator = avg_numerator_raw[metric_data_loaded["avg_numerator"]["field"]]
      elif metric_data_loaded['avg_numerator']['source'] == 'constant':
        print '[INFO][' + datadog_metric_name + '][' + project + '][' + metric_data_loaded['method'] + '] numerator data provider: ' + metric_data_loaded['avg_numerator']['source']
        avg_numerator = cp.provide(metric_data_loaded["avg_numerator"], project)
      else:
        print "[ERROR]: avg_numerator source is set to an unknown value: %s" % metric_data_loaded['avg_numerator']['source']

      if metric_data_loaded['avg_denominator']['source'] == 'jira':
        print '[INFO][' + datadog_metric_name + '][' + project + '][' + metric_data_loaded['method'] + '] denominator data provider: ' + metric_data_loaded['avg_denominator']['source']
        avg_denominator_raw = jp.provide(metric_data_loaded["avg_denominator"], project)
        avg_denominator = avg_denominator_raw[metric_data_loaded["avg_denominator"]["field"]]
      elif metric_data_loaded['avg_denominator']['source'] == 'constant':
        print '[INFO][' + datadog_metric_name + '][' + project + '][' + metric_data_loaded['method'] + '] denominator data provider: ' + metric_data_loaded['avg_denominator']['source']
        avg_denominator = cp.provide(metric_data_loaded["avg_denominator"], project)
      else:
        print "[ERROR]: avg_denominator source is set to an unknown value: %s" % metric_data_loaded['avg_denominator']['source']
  
      points = function_map[metric_file_method](avg_numerator, avg_denominator)

    ## Method: mean time between statuses
    if metric_data_loaded['method'] == 'mean_time_to_between_statuses':
      print '[INFO]: method: ' + metric_data_loaded['method']
      status_start_dates = []
      status_start = jp.provide(metric_data_loaded['status_start'], project)
      for issue_fields in status_start['issues']:
        status_start_dates.append(issue_fields['fields']['created'])
      status_end_dates = []
      status_end = jp.provide(metric_data_loaded['status_end'], project)
      for issue_fields in status_end['issues']:
        status_end_dates.append(issue_fields['fields']['updated'])

      status_dates = dict(zip(status_start_dates, status_end_dates))
      denominator_raw = jp.provide(metric_data_loaded["denominator"], project)
      denominator = denominator_raw[metric_data_loaded["denominator"]["field"]]

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

  # Upload to DataDog
  print('[INFO]: uploading to DataDog...')
  result = api.Metric.send(upload_payload)
  print('[INFO]: uploaded to DataDog')
