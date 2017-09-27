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

def results_per_given(results, metric_config, project):
  result = results[metric_config['key_needed']]
  given = metric_config['projects'][project]
  return int(result)/int(given)

function_map = {
  'results_per_given': results_per_given
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

metric_file_key_needed = metric_data_loaded['key_needed']
metric_file_method = metric_data_loaded['method']
datadog_metric_name = metric_data_loaded['metric_name']
jql_raw = metric_data_loaded['jql']

timestamp = time.time()
upload_payload = []

# JIRA api call
for project in metric_data_loaded['projects']:
  given = metric_data_loaded['projects'][project]
  jql_raw_regex = re.sub(r"{{project}}", project, jql_raw)
  jql_url_encoded = urllib.quote(jql_raw_regex)
  jira_api_call_url = api_endpoint + jql_url_encoded + "&maxResults=1000"
  jira_api_call = requests.get(jira_api_call_url, headers=headers, auth=(api_username, api_password))
  jira_api_results_json = json.loads(jira_api_call.text)
  metric_data = {
    'metric': datadog_metric_name,
    'points': (timestamp, function_map[metric_file_method](jira_api_results_json, metric_data_loaded, project)),
    'tags': ["jira_project:%s" % project]
    }
  upload_payload.append(metric_data) 

# DataDog api call: https://docs.datadoghq.com/api/#metrics-post
result = api.Metric.send(upload_payload)

print('Uploaded to DataDog')
