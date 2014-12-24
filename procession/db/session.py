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

import sqlalchemy
from sqlalchemy.orm import sessionmaker

import procession.db

LOG = logging.getLogger(__name__)

SESSION_MAKER = None
SESSION = None


def get_session():
    """
    Returns a `sqlalchemy.orm.session.Session` object that is global to this
    process.
    """
    global SESSION, SESSION_MAKER
    if SESSION is not None:
        return SESSION
    SESSION_MAKER = sessionmaker(bind=procession.db.ENGINE)
    SESSION = SESSION_MAKER(autocommit=False)
    return SESSION
