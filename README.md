# jiradog

A tool to poll data from JIRA to upload as a metric to DataDog.

## Prerequisites

Dependencies (outside of python standard library)
* JIRA
* DataDog
* pprint
* jinja2
* requests

## Installing

Clone the engineering_velocity_metrics project from the operations source control repository

## metrics.json syntax

How to build a metric.

The information you are pulling from JIRA is built around JIRA's own query language: JQL (JIRA Query Language). Here is an example section from the metrics.json file:
```
{
    "metric_name": "jiradog.avgOpenBugsPerDeveloper",
    "__comment": "SYS-1473",
    "projects": [
      "MACOSNOTE",
      "WINNOTE",
      "ION",
      "IOSNOTE",
      "DRDNOTE",
      "CE",
      "ENB"
      ],
    "method": "average",
    "avg_numerator": {
      "source": "jira",
      "jql": "project={{project}} AND issuetype=Bug AND status NOT IN (Done, Resolved, Closed)",
      "field": "total",
      "method": "ticket_count"
      },
    "avg_denominator": {
      "source": "constant",
      "data": {
        "MACOSNOTE": "7",
        "WINNOTE": "4",
        "ION": "9",
        "IOSNOTE": "8",
        "DRDNOTE": "7",
        "CE": "6",
        "ENB": "9"  
        }
      }
  }
```

Using standard JSON syntax we are defining what information to poll from JIRA, how to process it, and what to name the metric in DataDog.

```
     "metric_name": "jiradog.avgOpenBugsPerDeveloper",
```
The metric name in DataDog. After uploading to DataDog, this is the name you use when searching for the metric.

```
    "__comment": "SYS-1473",
```
The JSON spec doesn't define a way to handle in line comments. This is the 'official' jiradog comment method. Ensure all comment methods are prepended with two underscores ("\_"). In this case, the comment is the issue key that defined the creation of this metric.

```
    "projects": [
      "MACOSNOTE",
      "WINNOTE",
      "ION",
      "IOSNOTE",
      "DRDNOTE",
      "CE",
      "ENB"
      ],
```
Every metric needs a defined list of projects to run against. This must be a JSON list, even if there is only one value.

```
    "method": "average",
```
The 'method' defines the post-processing of the results returned from the JIRA API queries. In this case, we are finding the average between two data providers. The method also defines how the two data providers are labelled.

post-processing methods:
* **average**: Find the mean of 2 values.
* **mean\_time\_to\_between\_statuses**: Find the mean time between a status and last updated (for now).
* **direct**: Upload a direct result with no post-processing math.

```
    "avg_numerator": {
      "source": "jira",
      "jql": "project={{project}} AND issuetype=Bug AND status NOT IN (Done, Resolved, Closed)",
      "method": "ticket_count"
      },
```
For the method 'average', the script looks for both the 'avg_numerator' and 'avg_denominator' dictionaries in the metric config block. These are both data providers, describing the source and any needed information for getting what is needed.

In this case: We are getting information from Jira (`"source": "jira",`), and defines the JQL (`"jql": "project={{project}} AND issuetype=Bug AND status NOT IN (Done, Resolved, Closed)",`). A few things to note about the JQL: Instead of a hard-set project, there is a jinja2 style variable `{{project}}`. The script uses this jql string as a jinja2 template to build the actual JQL call. Later versions of the script will include other inline jinja2 style templates for more granularity.

Inside the data provider block here there is another `method` key-value pair. This is similar to the parent `method`, only applied to inside the data provider. Here we are looking for the total ticket count from this query.

per data provider methos:
* **ticket\_count**: Get the total issue count returned from the JIRA API poll.
* **custom\_field\_sum**: Get the sum of the values of a custom field.

```
    "avg_denominator": {
      "source": "constant",
      "data": {
        "__comment": "Total number of developers per project."
        "MACOSNOTE": "7",
        "WINNOTE": "4",
        "ION": "9",
        "IOSNOTE": "8",
        "DRDNOTE": "7",
        "CE": "6",
        "ENB": "9"  
        }
      }
```
The next data provider uses the source `constant`. This provider is for hard-coded information that is, well, constant. The comment adds some constext to what this information is. Right now the script only supports constant source separated by project.

### More on the metrics.json

The metrics.json file is a JSON list of dictionaries, each one a 'description'/'assertion' of what is needed out of JIRA, how to process, and what to name the metric in DataDog. Because it is json, be weary of JSON's strict syntax, especially with trailing/missing commas.

### Philosophy

The general philsophy is to use JQL to get the most specific results as possible, within the limitations of JQL. As I expand the script-based filtering, we want to rely on that as little as possible. script-based filtering will be removed if JQL gains the functionality we are looking for. When building a new metric, be as specific as possible with your JQL for issue searches and preferrably use no script-based filtering if possible.

## Authors

* **Bryce McNab** - *Initial work*
