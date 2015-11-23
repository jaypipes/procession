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

import testtools

from procession import config
from procession import context
from procession import exc
from procession import objects
from procession import search
from procession.storage.sql import models
from procession.storage.sql import driver

from tests import base
from tests import fixtures
from tests.storage.sql import fixtures as sql_fixtures


class TestSqlDriver(base.UnitTest):
    def setUp(self):
        super(TestSqlDriver, self).setUp()
        self.ctx = context.Context()
        store_conf = {
            'driver': 'sql',
            'connection': 'sqlite:///:memory:',
        }
        self.conf = config.Config(store=store_conf)
        self.driver = driver.Driver(self.conf)
        models.ModelBase.metadata.create_all(self.driver.engine)

    def test__get_session(self):
        self.assertIsNone(self.driver.session)
        sess = self.driver._get_session()
        self.assertIsNotNone(sess)
        self.assertIsNotNone(self.driver.session)

    def test_get_one_unknown_obj_type(self):
        class UnknownObject(objects.Object):
            pass

        with testtools.ExpectedException(exc.UnknownObjectType):
            self.driver.get_one(UnknownObject, 'fake-key')

    def test_get_one_not_found(self):
        filters = {
            'id': fixtures.NO_EXIST_UUID,
        }
        search_spec = search.SearchSpec(self.ctx, filters=filters)
        with testtools.ExpectedException(exc.NotFound):
            self.driver.get_one(objects.Organization, search_spec)

    def test_get_one(self):
        org = sql_fixtures.OrganizationInDb(self.driver.engine,
                                            models.ModelBase.metadata,
                                            id=fixtures.UUID1,
                                            name='fake-name',
                                            slug='fake-name',
                                            created_on=fixtures.CREATED_ON,
                                            root_organization_id=fixtures.UUID1,
                                            parent_organization_id=None,
                                            left_sequence=1,
                                            right_sequence=2)
        self.useFixture(org)
        filters = {
            'id': fixtures.UUID1,
        }
        search_spec = search.SearchSpec(self.ctx, filters=filters)
        r = self.driver.get_one(objects.Organization, search_spec)
        self.assertEqual(fixtures.UUID1, str(r['id']))
        self.assertEqual('fake-name', r['name'])
        self.assertEqual(fixtures.CREATED_ON, r['created_on'])
