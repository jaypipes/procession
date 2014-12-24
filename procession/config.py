# -*- encoding: utf-8 -*-
#
# Copyright 2013-2014 Jay Pipes
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import logging

DEFAULT_DB_CONNECTION = "sqlite:///"

DEFAULT_LOG_LEVEL = 'warning'
DEFAULT_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_LOG_FORMAT = ("%(asctime)s.%(msecs)03d %(process)d %(levelname)s "
                      "%(name)s %(message)s")

class LogConfig(object):
    def __init__(self, **options):
        self.conf_file = options.get('conf_file')
        self.date_format = options.get('date_format',
                                       DEFAULT_LOG_DATE_FORMAT)
        self.log_format = options.get('log_format',
                                      DEFAULT_LOG_FORMAT)
        self.log_level = getattr(logging,
                                 options.get('log_level',
                                             DEFAULT_LOG_LEVEL).upper())


class DBConfig(object):
    def __init__(self, **options):
        self.connection = options.get('connection', DEFAULT_DB_CONNECTION)


class Config(object):
    def __init__(self, **options):
        log_opts = options.get('log', {})
        self.log = LogConfig(**log_opts)
        db_opts = options.get('database', {})
        self.db = DBConfig(**db_opts)


def init(**options):
    return Config(**options)
