#!/usr/bin/env python

import datetime
import logging
import csv
import sys
import re
import pytz

from math import ceil
from jira import JIRA
from json import loads

JIRA_URL = ''
JIRA_LOGIN = ''
JIRA_PASSWORD = ''
JIRA_COM_TASK = ''
LOG_FILE = ''

with open('config.json') as configFile:
    config = loads(configFile.read())
    JIRA_URL = config['JIRA_URL']
    JIRA_LOGIN = config['JIRA_LOGIN']
    JIRA_PASSWORD = config['JIRA_PASSWORD']
    JIRA_COM_TASK = config['JIRA_COM_TASK']
    LOG_FILE = config['LOG_FILE']


class Worklog:
    def __init__(self, date: datetime.datetime, task_id: str, duration: datetime.timedelta, comment: str):
        self.date = date
        self.task_id = task_id
        self.duration = duration
        self.comment = comment


class Client:
    def report(self, worklog: Worklog) -> int:
        raise NotImplementedError()


class JiraLibClient(Client):
    def __init__(self, url: str, login: str, password: str):
        self._jira = JIRA(options={'server': url}, basic_auth=(login, password))

    def report(self, worklog: Worklog) -> int:
        date = worklog.date
        jira_worklog = self._jira.add_worklog(worklog.task_id, worklog.duration, comment=worklog.comment, started=date)
        return jira_worklog.id


class LoggingClient(Client):
    def __init__(self, wrapped: Client, logger: logging.Logger) -> None:
        self._wrapped = wrapped
        self._logger = logger

    def report(self, worklog: Worklog) -> int:
        log_id = self._wrapped.report(worklog)
        self._logger.debug('Created a worklog, id={id}. Task {task}, duration {duration}, date {date}'.format(
            id=log_id,
            task=worklog.task_id,
            duration=worklog.duration,
            date=worklog.date
        ))
        return log_id


def create_logger():
    logger = logging.getLogger('jira_worklog_creation')
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(LOG_FILE)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return logger


def format_timedelta(duration: str):
    t = datetime.datetime.strptime(duration, "%H:%M:%S")
    # ...and use datetime's hour, min and sec properties to build a timedelta
    delta = datetime.timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)

    hours = int(delta.total_seconds() // 3600)
    minutes = ceil((delta.total_seconds() - hours * 3600) / 60)

    return '{hours:02d}h {minutes:02d}m'.format(hours=hours, minutes=minutes)


if __name__ == '__main__':
    jira = LoggingClient(JiraLibClient(JIRA_URL, JIRA_LOGIN, JIRA_PASSWORD), create_logger())

    with open(sys.argv[1]) as fp:
        file = csv.DictReader(fp)
        for row in file:
            task_raw = re.search('[A-Z]+-[0-9]+', row['Description'])
            task = JIRA_COM_TASK if task_raw is None else task_raw.group(0)
            worklog = Worklog(
                datetime.datetime.strptime(
                    "{}T{}+0300".format(row['Start date'], row['Start time']),  # Захардкоженный часовой пояс
                    '%Y-%m-%dT%H:%M:%S%z'
                ).astimezone(pytz.utc),
                task,
                format_timedelta(row['Duration']),
                re.sub("\s*{}\s*".format(task), '', row['Description'])
            )
            print("Задача: {}\nВремя: {} ({})\nКомментарий: {}\n".format(
                worklog.task_id,
                worklog.date.strftime("%Y-%m-%dT%H:%M:%S%z"),
                worklog.duration,
                worklog.comment
            ))
            jira.report(worklog)
