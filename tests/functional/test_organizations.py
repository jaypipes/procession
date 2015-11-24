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

from procession import config
from procession import context
from procession import objects
from procession import search
from procession import store
from procession.storage.sql import models

from tests import base
from tests.functional import helpers
from tests import mocks


class TestOrganizations(base.UnitTest):
    def setUp(self):
        super(TestOrganizations, self).setUp()
        self.ctx = context.Context()
        store_conf = {
            'driver': 'sql',
            'connection': 'sqlite:///:memory:',
        }
        self.conf = config.Config(store=store_conf)
        self.store = store.Store(self.conf)
        models.ModelBase.metadata.create_all(self.store.driver.engine)

    def test_get_one(self):
        org = helpers.OrganizationInDb(
            self.store.driver.engine,
            models.ModelBase.metadata,
            id=mocks.UUID1,
            name='fake-name',
            slug='fake-name',
            created_on=mocks.CREATED_ON,
            root_organization_id=mocks.UUID1,
            parent_organization_id=None,
            left_sequence=1,
            right_sequence=2,
        )
        self.useFixture(org)
        filters = {
            'id': mocks.UUID1,
        }
        search_spec = search.SearchSpec(self.ctx, filters=filters)
        r = self.store.get_one(objects.Organization, search_spec)
        self.assertEqual(mocks.UUID1, str(r['id']))
        self.assertEqual('fake-name', r['name'])
        self.assertEqual(mocks.CREATED_ON, r['created_on'])
