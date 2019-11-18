#!/usr/bin/env python

import datetime
import logging
import csv
import re
import pytz

from math import ceil
from jira import JIRA
from json import loads
from glob import glob
from sys import argv, exit
from os import remove

JIRA_URL = ''
JIRA_LOGIN = ''
JIRA_PASSWORD = ''
JIRA_COM_TASK = ''
LOG_FILE = ''
CSV_DURATION = ''
CSV_DESCRIPTION = ''
CSV_START_DATE = ''
CSV_START_TIME = ''

with open('config.json') as configFile:
    config = loads(configFile.read())
    JIRA_URL = config['JIRA_URL']
    JIRA_LOGIN = config['JIRA_LOGIN']
    JIRA_PASSWORD = config['JIRA_PASSWORD']
    JIRA_COM_TASK = config['JIRA_COM_TASK']
    LOG_FILE = config['LOG_FILE']
    DOWNLOADS_PATH = config['DOWNLOADS_PATH']
    CSV_DURATION = config['CSV_DURATION']
    CSV_DESCRIPTION = config['CSV_DESCRIPTION']
    CSV_START_DATE = config['CSV_START_DATE']
    CSV_START_TIME = config['CSV_START_TIME']



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


def get_csv_file_name():
    if (DOWNLOADS_PATH):
        csv_files = glob(DOWNLOADS_PATH + '/*.csv')
        if 1 == len(csv_files):
            return csv_files[0]

    if (len(argv) > 1):
        return argv[1]

    return None


if __name__ == '__main__':
    jira = LoggingClient(JiraLibClient(JIRA_URL, JIRA_LOGIN, JIRA_PASSWORD), create_logger())

    csv_file_name = get_csv_file_name()

    if (csv_file_name is None):
        print('CSV file name not specified')
        exit()

    with open(csv_file_name, encoding='utf-8') as fp:
        file = csv.DictReader(fp)
        for row in file:
            task_raw = re.search('[A-Z]+-[0-9]+', row[ CSV_DESCRIPTION])
            task = JIRA_COM_TASK if task_raw is None else task_raw.group(0)
            worklog = Worklog(
                datetime.datetime.strptime(
                    "{}T{}+0300".format(row[CSV_START_DATE], row[CSV_START_TIME]),  # Захардкоженный часовой пояс
                    '%Y-%m-%dT%H:%M:%S%z'
                ).astimezone(pytz.utc),
                task,
                format_timedelta(row[CSV_DURATION]),
                re.sub("\s*{}\s*".format(task), '', row[CSV_DESCRIPTION])
            )
            print("Задача: {}\nВремя: {} ({})\nКомментарий: {}\n".format(
                worklog.task_id,
                worklog.date.strftime("%Y-%m-%dT%H:%M:%S%z"),
                worklog.duration,
                worklog.comment
            ))
            jira.report(worklog)
    remove(csv_file_name)
