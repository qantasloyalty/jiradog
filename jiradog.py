#!/usr/bin/python

import sys
import requests
import json
import io
import urllib
import re

config_file = '/etc/jiradog.conf'
metric_file = sys.argv[1]
headers = {'Content-type': 'application/json'}
upload_payload = {}

with open(config_file) as config_data_file:
  config_data_loaded = json.load(config_data_file)

api_username = config_data_loaded['username']
api_password = config_data_loaded['password']
api_url = config_data_loaded['server']
api_endpoint = api_url + '/rest/api/2/search?jql='

with open(metric_file) as metric_data_file:
  metric_data_loaded = json.load(metric_data_file)

metric_file_key_needed = metric_data_loaded['key_needed']

jql_raw = metric_data_loaded['jql']

for project in metric_data_loaded['projects']:
  jql_raw_regex = re.sub(r"{{project}}", project, jql_raw)
  jql_url_encoded = urllib.quote(jql_raw_regex)
  jira_api_call_url = api_endpoint + jql_url_encoded + "&maxResults=1000"
  jira_api_call = requests.get(jira_api_call_url, headers=headers, auth=(api_username, api_password))
  jira_api_results_json = json.loads(jira_api_call.text)
  value_needed = jira_api_results_json[metric_file_key_needed]
  upload_payload[project] = value_needed

print upload_payload
