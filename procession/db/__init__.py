#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#
# Copyright 2013 Jay Pipes
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

from oslo.config import cfg

database_opts = [
    cfg.StrOpt('connection',
               default='sqlite:///',
               help='The SQLAlchemy connection string used to connect to the '
                    'database when writing data or when reading data and the '
                    'caller cannot tolerate any replication lag.',
               secret=True),
    cfg.StrOpt('low_priority_connection',
               default=None,
               help='The SQLAlchemy connection string used to connect to the '
                    'database when reading data and the caller may tolerate '
                    'some level of replication lag or delay[.',
               secret=True),
    cfg.IntOpt('connection_debug',
               default=0,
               help='Verbosity of SQL debugging information. 0=None, '
                    '100=Everything'),
    cfg.BoolOpt('connection_trace',
                default=False,
                help='Add python stack traces to SQL as comment strings.'),
]

CONF = cfg.CONF
CONF.register_opts(database_opts, 'database')
