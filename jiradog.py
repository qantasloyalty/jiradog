#!/usr/bin/python

from datadog import initialize, api
from pprint import pprint
from jira import JIRA
import jinja2, argparse, sys, requests, json, io, urllib, re, time, logging 

class jira_provider(object):
  """This creates the paginated URLS (multiple urls to hit because the total results exceed the maximum allowable returned results) and calls the API, returning results.

  Args:
      provider_config:	Dictionary, the part of the config that defines the data provider source, and JQL query string.
      project:		String, the JIRA project that will be put into the templatized JQL query string.
      max_results:	Integer, currently hard set at 100, maximum supported by JIRA.
      username:		String, the username of the user who is being used to access the API over basic HTTP auth.
      password:		String, password of the above user.
      server:		String, JIRA server url instance; where to hit the API.

  Returns:
      A list of dictionaries that are the JSON objects returned by the API calls. All URLS are generated by the paginate function.
  """

  def issue_filter(self, paginated_list, filter_jinja2):
    """Filters issues with a jinja2 syntax if/then statement.

    Args:
        paginated_list	List	Of dictionaries of lists of issues returned from paginated JIRA API calls.
        filter_jinja2:	String	jinja2 syntax if/then statement for filterin, found in the metric config.

    Returns:
        List of dictionaries of lists of issues.
    """
    filtered_list = []
    operators = '~|=|!='
    filter_jinja2_regex = re.search("(^{% if )(.*)( )("+ operators +")( ')(.*)(' %}$)",filter_jinja2)
    fields = filter_jinja2_regex.group(2).split('.')
    operator = filter_jinja2_regex.group(4)
    value = filter_jinja2_regex.group(6)
    issue_list = []
    issues = []
    for page in paginated_list:
      for issue in page['issues']:
        regex_result = re.search(value, issue[fields[1]][fields[2]][int(fields[3])][fields[4]])
        if type(regex_result) != type(None):
          print issue['key']
          issues.append(issue)
#         paginated_list[paginated_list.index(page)]['issues'].remove(issue)
    issue_list.append({'issues': issues})
    return issue_list
#   return paginated_list

  def paginate(self, base_api_url, total, max_results):
    """Create a list of JIRA API search urls appended with '&startAt=N' in order to get all results from a JQL query.

    Args:
        base_api_url:	String, the specified API url, given by the provide function, derived from the jql key in the metric config file.
        total:		Integer, total number of issues, pulled from the original API call.
        max_results:	Integer, currently hard set at 100, maximum supported by JIRA.

    Returns:
        A list of urls, with the appended '&startAt=N' that, when looped, will pull all JQL search results.
    """
    paginations = []
    start_at = max_results
    while (int(start_at) < int(total)):
      paginations.append(base_api_url + '&startAt=' + str(start_at))
      start_at = int(start_at) + int(max_results)
    return paginations

  def provide(self, provider_config, project, max_results):
    """Makes API calls using the JIRA API, version 2, search.

    Args:
        provider_config:	Dictionary, the part of the config that defines the data provider source, and JQL query string.
        project:		String, the JIRA project that will be put into the templatized JQL query string.
        max_results:		Integer, currently hard set at 100, maximum supported by JIRA.

    Returns:
        A list of dictionaries that are the JSON objects returned by the API calls. All URLS are generated by the paginate function.
    """
    jql_template = jinja2.Template(provider_config["jql"])
    jql_rendered = jql_template.render(project=project)
    jql_url_encoded = urllib.quote(jql_rendered)
    jira_api_call_url = api_endpoint + jql_url_encoded + '&maxResults=' + max_results
    jira_api_response = json.loads(requests.get(jira_api_call_url, headers=headers, auth=(api_username, api_password)).text)
    jira_api_responses = [jira_api_response]
    for url in self.paginate(jira_api_call_url, jira_api_response['total'], max_results):
      jira_api_response = requests.get(url, headers=headers, auth=(api_username, api_password))
      jira_api_responses.append(json.loads(jira_api_response.text))
    paginated_list = self.issue_filter(jira_api_responses, provider_config['filter'])
    return paginated_list
#   return jira_api_responses

class constant_provider(object):
  """Data provider for data hard-coded in the metric config file.

  Args:
      data:                   Dictionary      Data from the metric config file.
      project:                String          The JIRA project; used to get data from the imported dictionary.
      NULL_max_results:       Integer         NULL metric, to allow generalized usaged. Unused by this function.

  Returns:
      A single value from a hard coded dictionary included the in the metric config file.
  """
  def provide(self, data, project, NULL_max_results):
    """Retrieves and retunrs explicit data hard-coded into the metric config file.

    Args:
        data:			Dictionary	Data from the metric config file.
        project:		String		The JIRA project; used to get data from the imported dictionary.
        NULL_max_results:	Integer		NULL metric, to allow generalized usaged. Unused by this function.

    Returns:
        A single value from a hard coded dictionary included the in the metric config file.	
    """
    return data["data"][project]

def average(numerator, denominator):
  """Finds the average of 2 numbers.

  Args:
      numerator:	Integer		The numerator, found using one of the data providers.
      denominator:	Integer		The denominator, found using one of the data providers.

  Returns:
      Integer of the resulting division. If the denominator is 0, sets the returned value as 0.
  """
  if denominator != 0:
    return float(numerator)/float(denominator)
  else:
    return 0

def mean_time_to_between_statuses(first_date, second_date):
  """Calculates the length of time between two statuses

  Args:
      first_date:	String	A simple string of the start date in the format '%Y-%m-%dT%H:%M:%S'
      second_date:	String	A simple string of the end date in the format '%Y-%m-%dT%H:%M:%S'

  Returns:
      Floating point number in days
  """
  first_date_sec = time.strptime(first_date.split('.')[0],'%Y-%m-%dT%H:%M:%S')
  second_date_sec = time.strptime(second_date.split('.')[0],'%Y-%m-%dT%H:%M:%S')
  return (time.mktime(second_date_sec) - time.mktime(first_date_sec)) / 60 / 60 / 24

def ticket_count(paginated_list, null_field):
  """Gets the count of issues from a JQL query result.

  Args:
      result:		List	A single page from an API call.
      null_field:	None	Used to allow automating method type.

  Returns:
      Integer of the number of issues counted.
  """
  total_issues = 0
  for page in paginated_list:
    total_issues = total_issues + len(page['issues'])
  return total_issues
# return len(result['issues'])

def custom_field_sum(result, custom_field):
  """Sums custom field values together.

  Args:
      result:		Dictionary	The result from a JIRA JQL query.
      custom_field:	String		The custom field to sum.

  Returns:
      Integer of the sum of all the found values of the custom_field.
  """
  custom_field_sum = 0
  for issue in result['issues']:
    if issue['fields'][custom_field] is None:
      custom_field_sum = int(custom_field_sum) + 2
    else:
      custom_field_sum = int(custom_field_sum) + int(issue['fields'][custom_field])
  return custom_field_sum

def get_number_average(provider_config, position, project):
  """Gets and returns either numerator or denominator for average method from metric config file and data provider

  Args:
      provider_config:	Dictionary	Pulled from the metric config, contains source, and arguments.
      position:		String		Indicates if this is the numerator or denominator
      project:		String		The jira project being injected into the templatized JQL query string.

  Returns:
      A float to act as the numerator.
  """
  if provider_config['source'] == 'jira':
    logging.info('data provider: ' + provider_config['source'])
    paginated_list = jira_provider().provide(provider_config, project, max_results)
    running_total = []
    for result in paginated_list:
      running_total.append(function_map[provider_config['method']](result, provider_config['field']))
    number = sum(running_total)
    logging.info(position + ': ' + str(number))
  elif provider_config['source'] == 'constant':
    logging.info('data provider: ' + provider_config['source'])
    number = constant_provider().provide(provider_config, project, max_results)
    logging.info(position + ': ' + str(number))
  else:
    logging.error('avg_' + position + ' ' + 'data provider is set to an unknown value: ' + provider_config['source'])
    sys.exit(1)
  return number

def direct(provider_config, project):
  """Gets a single number from JIRA and submits it to DataDog.

  Args:
      provider_config:	Dictionary	Pulled from the metric config, contains source, and arguments.
      project:		String		The jira project being injected into the templatized JQL query string.

  Returns:
      Integer of the results from JIRA API requests.
  """
  if provider_config['source'] == 'jira':
    logging.info('data provider: ' + provider_config['source'])
    paginated_list = jira_provider().provide(provider_config, project, max_results)
    running_total = []
    for result in paginated_list:
      running_total.append(function_map[provider_config['method']](result,None))
    return sum(running_total)

def main(argv):
  parser = argparse.ArgumentParser()
  parser.add_argument('-m', '--metric',
    help='Run only the specific metric name from metrics.json')

  args = parser.parse_args()

  logging.info('api configuration set')

  # Setting up DataDog SDK
  initialize(**config_data_loaded['datadog'])
  logging.info('initializated datadog SDK')

  # Loads the metric configuration file
  with open(metric_json) as metric_file:
    metric_file_full = json.load(metric_file)
  if args.metric:
    for metric_config in metric_file_full:
      if metric_config['metric_name'] == args.metric:
        metric_file_full = [metric_config]

  logging.info('loaded metric config')

  # Loops through all command line arguments, which is a space delimited list of metric configuration files.
  for metric_data_loaded in metric_file_full:
    log_prepend = '[INFO]'

    metric_file_method = metric_data_loaded['method']
    datadog_metric_name = metric_data_loaded['metric_name']

    timestamp = time.time()
    upload_payload = []

    # Loop over specified projects in the metric config file.
    for project in metric_data_loaded['projects']:
      logging.info('project: ' + project)
      if metric_data_loaded['method'] == 'average':
        ## Find the average from data providers in metric configuration file.
        logging.info('method: ' + metric_data_loaded['method'])
        avg_numerator = get_number_average(metric_data_loaded['avg_numerator'], 'numerator', project)
        avg_denominator = get_number_average(metric_data_loaded['avg_denominator'], 'denominator', project)
        points = function_map[metric_file_method](avg_numerator, avg_denominator)
      elif metric_data_loaded['method'] == 'mean_time_to_between_statuses':
        ## Find the average time between specified statuses.
        logging.info('method: ' + metric_data_loaded['method'])

        date_diff_days = []
        paginated_list = jira_provider().provide(metric_data_loaded['issues'], project, max_results)
        print len(paginated_list[0]['issues'])
        if len(paginated_list) != 0:
          for status_dates in paginated_list:
            for issue_fields in status_dates['issues']:
              date_diff_days.append(mean_time_to_between_statuses(issue_fields['fields']['created'],issue_fields['fields']['updated']))
          total_time_between_statuses = sum(date_diff_days)
          total_issue_count = ticket_count(paginated_list, None)
#         total_issue_count = paginated_list[0]['total']

        if total_issue_count != 0:
          points = average(total_time_between_statuses, total_issue_count)
        else:
          points = 0
      elif metric_data_loaded['method'] == 'direct':
        points = direct(metric_data_loaded['issues'], project)

      ## Construct payload for upload
      metric_data = {
        'metric': datadog_metric_name,
        'points': (timestamp, points),
        'tags': ["jira_project:%s" % project]
        }
      upload_payload.append(metric_data) 

    logging.info('payload: ' + str(upload_payload))

    # Upload to DataDog
    result = api.Metric.send(upload_payload)
    logging.info('uploaded to DataDog')

if __name__ == "__main__":
  # Setting important variables, all static.
  function_map = {
    'average': average,
    'mean_time_to_between_statuses': mean_time_to_between_statuses,
    'ticket_count': ticket_count,
    'custom_field_sum': custom_field_sum,
    'direct': direct
  }
  max_results = str(100)
  config_file = 'config.json'
  log_prepend = '[INFO]'
  headers = {'Content-type': 'application/json'}
  upload_payload = {}
  
  # Loads the configuration file for the script.
  with open(config_file) as config_data_file:
    config_data_loaded = json.load(config_data_file)

  # Set important information scraped from the configuration file.
  api_username = config_data_loaded['jira']['username']
  api_password = config_data_loaded['jira']['password']
  api_url = config_data_loaded['jira']['server']
  api_endpoint = api_url + '/rest/api/2/search?jql='
  log_file = config_data_loaded['local']['log_file']
  metric_json = config_data_loaded['local']['metric_file']
  
  # Set logging config
  logging_levels = {
    'info': logging.INFO,
    'debug': logging.DEBUG,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL
    }
  logging_level = logging_levels.get('debug', logging.NOTSET)
  logging.basicConfig(filename=log_file, format='%(asctime)s %(levelname)s %(message)s', level=logging_level)

  # Executing script 
  main(sys.argv)
