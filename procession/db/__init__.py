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

import sqlalchemy
from sqlalchemy.orm import sessionmaker

from procession.db import models

ENGINE = None


def init(conf):
    """
    Initialize the database connection and sessionmaker for the Procession
    server worker(s).

    :param conf: `procession.config.Config` object.
    """
    db_connection = conf.db.connection
    global ENGINE
    if ENGINE is not None:
        return ENGINE
    ENGINE = sqlalchemy.create_engine(db_connection)
    models.ModelBase.metadata.create_all(ENGINE)
