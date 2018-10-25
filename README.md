# Toggle to Jira

This script can parse your [Toggl](http://toggl.com) work logs (CSV export) and upload them to [Jira](http://jira.com).
Initially written by [Roman Savinkov](mailto:r.savinkov@gmail.com).

## Requirements
* Linux / macOS
* Python 3

## Using in Python Virtual Environment

* Setup [venv](https://docs.python.org/3/tutorial/venv.html) by running `./install.sh`
* Configure Jira access and personal settings by editing `config.json`
* Run the script inside virtual environment `./report.sh <toggl_report.csv>`
