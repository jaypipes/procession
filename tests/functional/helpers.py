# -*- encoding: utf-8 -*-
#
# Copyright 2015 Jay Pipes
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

import fixtures


class OrganizationInDb(fixtures.Fixture):
    def __init__(self, engine, metadata, **values):
        self.values = values
        self.engine = engine
        self.metadata = metadata
        self.orgs = metadata.tables['organizations']

    def remove_from_db(self):
        id_col = self.orgs.c.id
        delete = self.orgs.delete().where(id_col == self.values['id'])
        conn = self.engine.connect()
        conn.execute(delete)

    def _setUp(self):
        ins = self.orgs.insert().values(**self.values)
        conn = self.engine.connect()
        conn.execute(ins)
        self.addCleanup(self.remove_from_db)
