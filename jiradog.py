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
    return jira_api_response[provider_config["field"]]

class constant_provider(object):
  def __init__(self):
    pass
  
  def provide(self, data, project):
    return data["data"][project]

def average(avg_numerator, avg_denominator, project):
  return float(avg_numerator)/float(avg_denominator)

function_map = {
  'avg': average
}

config_file = '/etc/jiradog.conf'
metric_file = sys.argv[1]
headers = {'Content-type': 'application/json'}
upload_payload = {}

with open(config_file) as config_data_file:
  config_data_loaded = json.load(config_data_file)

api_username = config_data_loaded['jira']['username']
api_password = config_data_loaded['jira']['password']
api_url = config_data_loaded['jira']['server']
api_endpoint = api_url + '/rest/api/2/search?jql='
initialize(**config_data_loaded['datadog'])

with open(metric_file) as metric_data_file:
  metric_data_loaded = json.load(metric_data_file)

metric_file_method = metric_data_loaded['method']
datadog_metric_name = metric_data_loaded['metric_name']

jp = jira_provider(api_username, api_password, api_url)
cp = constant_provider()

timestamp = time.time()
upload_payload = []

# JIRA api call
for project in metric_data_loaded['projects']:
  if metric_data_loaded['method'] == 'avg':

    if metric_data_loaded['avg_numerator']['source'] == 'jira':
      avg_numerator = jp.provide(metric_data_loaded["avg_numerator"], project)
    elif metric_data_loaded['avg_numerator']['source'] == 'constant':
      avg_numerator = cp.provide(metric_data_loaded["avg_numerator"], project)
    else:
      print "[ERROR]: avg_numerator source is set to an unknown value: %s" % metric_data_loaded['avg_numerator']['source']

    if metric_data_loaded['avg_denominator']['source'] == 'jira':
      avg_denominator = jp.provide(metric_data_loaded["avg_denominator"], project)
    elif metric_data_loaded['avg_denominator']['source'] == 'constant':
      avg_denominator = cp.provide(metric_data_loaded["avg_denominator"], project)
    else:
      print "[ERROR]: avg_denominator source is set to an unknown value: %s" % metric_data_loaded['avg_denominator']['source']

    metric_data = {
      'metric': datadog_metric_name,
      'points': (timestamp, function_map[metric_file_method](avg_numerator, avg_denominator, project)),
      'tags': ["jira_project:%s" % project]
      }

    upload_payload.append(metric_data) 

# DataDog api call: https://docs.datadoghq.com/api/#metrics-post
# pprint(upload_payload)
result = api.Metric.send(upload_payload)

print('Uploaded to DataDog')
