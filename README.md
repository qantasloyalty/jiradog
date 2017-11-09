# jiradog

Version 1.1.2
A tool to poll data from JIRA to upload as a metric to DataDog.

## Prerequisites

Dependencies (outside of python standard library)
* JIRA
* DataDog
* pprint
* jinja2

## Installing

Clone the engineering\_velocity\_metrics project from the operations source control repository

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
    "numerator": {
      "source": "jira",
      "jql": "project={{project}} AND issuetype=Bug AND status NOT IN (Done,Resolved,Closed)",
      "method": "ticket_count"
      },
    "denominator": {
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
    "numerator": {
      "source": "jira",
      "jql": "project={{project}} AND issuetype=Bug AND status NOT IN (Done, Resolved, Closed)",
      "method": "ticket_count"
      },
```
For the method 'average', the script looks for both the 'numerator' and 'denominator' dictionaries in the metric config block. These are both data providers, describing the source and any needed information for getting what is needed.

In this case: We are getting information from Jira (`"source": "jira",`), and defines the JQL (`"jql": "project={{project}} AND issuetype=Bug AND status NOT IN (Done, Resolved, Closed)",`). A few things to note about the JQL: Instead of a hard-set project, there is a jinja2 style variable `{{project}}`. The script uses this jql string as a jinja2 template to build the actual JQL call. Later versions of the script will include other inline jinja2 style templates for more granularity.

Inside the data provider block here there is another `method` key-value pair. This is similar to the parent `method`, only applied to inside the data provider. Here we are looking for the total ticket count from this query.

per data provider methos:
* **ticket\_count**: Get the total issue count returned from the JIRA API poll.
* **custom\_field\_sum**: Get the sum of the values of a custom field.

```
    "denominator": {
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

### script-based filtering
We use a jinja2/nunjucks style filtering with if/then statements. JQL currently doesn't support selecting fixVersions with a "~" (contains) or "LIKE" operator. To get around this, take a look at the `filter` key-value pair in this example data provider block:

```
    "issues": {
      "__comment": "List of issues released to GA (Global Acceptance)/Production",
      "source": "jira",
      "jql": "Project={{project}} AND issuetype=Story AND fixVersion!=EMPTY AND resolved>endOfDay(-180d)",
      "filter": "{% if 'GA' in issue.fields.fixVersions[0].name %}true{% endif %}"
      }
```

Following the typical jinja2 if/then statement, we have the statement, which is declared by the surrounding `{%` and `%}`. Inside is a basic structure: `if issue.fields.fixVersions.0.name ~ 'GA'`. `issue.fields.fixVersions.0.name` is the 'path' of the key-value pair in the issue we are looking to compare with the value, in this case `GA`. This will filter all issues to see if they have a `fixVerions` that contains `GA`.

### More on the metrics.json

The metrics.json file is a JSON list of dictionaries, each one a 'description'/'assertion' of what is needed out of JIRA, how to process, and what to name the metric in DataDog. Because it is json, be wary of JSON's strict syntax, especially with trailing/missing commas.

### Philosophy

The general philsophy is to use JQL to get the most specific results as possible, within the limitations of JQL. As I expand the script-based filtering, we want to rely on that as little as possible. script-based filtering will be removed if JQL gains the functionality we are looking for. When building a new metric, be as specific as possible with your JQL for issue searches and preferrably use no script-based filtering if possible.

### Style guide

#### JQL

None of the following styles, whether followed or not, will break script functionality.

##### Whitespace
Here is a correctly styled JQL query.
`project={{project}} AND issuetype=Bug AND status NOT IN (Done,Resolved,Closed)`

The 'official' whitespace rules are:

- Whitespace = SPACE (`U+0020`)
- No _leading_ or _trailing_ whitespace
- One whitespace character maximum concurrently (there should be no double spaces)
- In paranthesized groups, no whitespace following comma: `(Done,Resolved,Closed)`

##### Fields

When referencing a field in JQL, use camelCase:

- `project`
- `issueType`
- `fixVersions`
- `resolved`
- `updatedDate`

##### Operators

Operators are used to join several conditions or expand on a condition.

- Operators must be written in UPPERCASE (`AND`, `WAS`, `OR`, `NOT`, `IN`, etc)
- Operators should be surrounded by whitespace (`x AND y`, `status NOT IN (foo,bar)`)
- Mathmatical operators (=, !=, >, <, >=, <=, etc) should not be surrounded by whitespace (`x=4`, `assignee!=currentUser()`, `updated>=endOfDay(-90d)`)

#### Jinja2

None of the following styles, whether followed or not, will break script functionality.

##### Spacing

Lifted from the jinja2 style guide from the chromium project: https://www.chromium.org/developers/jinja#TOC-Spacing

```
  {{foo}}
  {{foo | filter}}
  {% for i in x|filter %}
```

> I.e., no spacing within {{}}, but do space around |, except in block control statements. This is the opposite of Jinja spec convention, which is {{ foo }} and {{ foo|filter }} – reasoning is that {{}} are functioning like parentheses or quotes, hence no spacing inside them; while | is functioning like a binary operator, like arithmetic operations, hence spaces around it. However, in block control statements | has higher precedence than the control flow keywords, and thus omitting spaces makes the precedence clearer.
More pragmatically, {{}} is very widely used for variable substitution, hence want to keep it short and looking like a single unit, while usage of filters via | is logically complex, and thus should stick out visually, with the steps in the pipeline clearly separated. However, adding spaces within a block control statement makes it confusing, due to the spaces around the control flow keywords, and thus spaces around | should be omitted. (von Barth, "Jinja")

##### Comments

> If a block is long, particularly if it is nested, please add a comment at the end to help clarify which block is ending; use the same content as the if condition or for list. (von Barth, "Jinja")

Example comment:

```
{# foo #}
```

## Citations
Von Barth, N. (n.d.). Jinja. Retrieved November 09, 2017, from
    https://www.chromium.org/developers/jinja#TOC-Spacing
    
Von Barth, N. (n.d.). Jinja. Retrieved November 09, 2017, from
    https://www.chromium.org/developers/jinja#TOC-Comment-end-of-long-blocks

## Authors

* **Bryce McNab** - *Initial work* - 11/09/2017
