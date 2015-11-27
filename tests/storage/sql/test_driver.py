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

import mock
import testtools

from procession import config
from procession import context
from procession import exc
from procession import objects
from procession import search
from procession.storage.sql import models
from procession.storage.sql import driver

from tests import base
from tests import mocks


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
            'id': mocks.NO_EXIST_UUID,
        }
        search_spec = search.SearchSpec(self.ctx, filters=filters)
        with testtools.ExpectedException(exc.NotFound):
            self.driver.get_one(objects.Organization, search_spec)

    @mock.patch('procession.storage.sql.api.get_one')
    @mock.patch('procession.storage.sql.driver.Driver._get_session')
    def test_get_one(self, sess_mock, api_mock):
        sess_mock.return_value = mock.sentinel.session
        db_model_mock = mock.MagicMock()
        db_model_mock.to_dict.return_value = mock.sentinel.to_dict
        api_mock.return_value = db_model_mock

        filters = {
            'id': mocks.UUID1,
        }
        search_spec = search.SearchSpec(self.ctx, filters=filters)
        r = self.driver.get_one(objects.Organization, search_spec)

        self.assertEqual(mock.sentinel.to_dict, r)
        api_mock.assert_called_once_with(mock.sentinel.session,
                                         models.Organization,
                                         id=mocks.UUID1)

    @mock.patch('procession.storage.sql.api.get_many')
    @mock.patch('procession.storage.sql.driver.Driver._get_session')
    def test_get_many(self, sess_mock, api_mock):
        sess_mock.return_value = mock.sentinel.session
        db_model_mock = mock.MagicMock()
        db_model_mock.to_dict.return_value = mock.sentinel.to_dict
        api_mock.return_value = [db_model_mock]

        filters = {
            'name': 'fake-name',
        }
        search_spec = search.SearchSpec(self.ctx, filters=filters)
        r = self.driver.get_many(objects.Organization, search_spec)

        self.assertEqual([mock.sentinel.to_dict], r)
        api_mock.assert_called_once_with(mock.sentinel.session,
                                         models.Organization,
                                         search_spec)

    @mock.patch('procession.storage.sql.api.exists')
    @mock.patch('procession.storage.sql.driver.Driver._get_session')
    def test_exists(self, sess_mock, api_mock):
        sess_mock.return_value = mock.sentinel.session
        api_mock.return_value = mock.sentinel.exists

        r = self.driver.exists(objects.Organization, mock.sentinel.key)

        self.assertEqual(mock.sentinel.exists, r)
        api_mock.assert_called_once_with(mock.sentinel.session,
                                         models.Organization,
                                         mock.sentinel.key)

    @mock.patch('procession.storage.sql.driver.Driver._get_session')
    def test_get_relations_invalid_relation(self, sess_mock):
        sess_mock.return_value = mock.sentinel.session

        filters = {
            'name': 'fake-user',
        }
        user_search_spec = search.SearchSpec(self.ctx, filters=filters)
        with testtools.ExpectedException(exc.InvalidRelation):
            self.driver.get_relations(objects.User, objects.Domain,
                                      user_search_spec)

    @mock.patch('procession.storage.sql.api.user_groups_get')
    @mock.patch('procession.storage.sql.driver.Driver._get_session')
    def test_get_relations(self, sess_mock, api_mock):
        sess_mock.return_value = mock.sentinel.session
        db_model_mock = mock.MagicMock()
        db_model_mock.to_dict.return_value = mock.sentinel.to_dict
        api_mock.return_value = [db_model_mock]

        filters = {
            'name': 'fake-user',
        }
        user_search_spec = search.SearchSpec(self.ctx, filters=filters)
        r = self.driver.get_relations(objects.User, objects.Group,
                                      user_search_spec)

        self.assertEqual([mock.sentinel.to_dict], r)
        api_mock.assert_called_once_with(mock.sentinel.session,
                                         user_search_spec,
                                         None)

        api_mock.reset_mock()
        filters = {
            'name': 'fake-group',
        }
        group_search_spec = search.SearchSpec(self.ctx, filters=filters)
        r = self.driver.get_relations(objects.User, objects.Group,
                                      user_search_spec,
                                      group_search_spec)

        self.assertEqual([mock.sentinel.to_dict], r)
        api_mock.assert_called_once_with(mock.sentinel.session,
                                         user_search_spec,
                                         group_search_spec)

    @mock.patch('procession.storage.sql.api.organization_delete')
    @mock.patch('procession.storage.sql.driver.Driver._get_session')
    def test_delete(self, sess_mock, api_mock):
        sess_mock.return_value = mock.sentinel.session
        api_mock.return_value = mock.sentinel.delete

        self.driver.delete(objects.Organization, mock.sentinel.key)

        api_mock.assert_called_once_with(mock.sentinel.session,
                                         mock.sentinel.key)

    @mock.patch('procession.storage.sql.api.organization_create')
    @mock.patch('procession.storage.sql.driver.Driver._get_session')
    def test_save_new_object(self, sess_mock, api_mock):
        sess_mock.return_value = mock.sentinel.session
        model_mock = mock.MagicMock()
        model_mock.to_dict.return_value = {
            'id': str(mocks.UUID1),
            'name': 'org name',
            'slug': 'org-name',
            'parent_organization_id': '',
            'root_organization_id': str(mocks.UUID1),
            'created_on': str(mocks.CREATED_ON),
            'left_sequence': 1,
            'right_sequence': 2,
        }
        api_mock.return_value = model_mock
        values = {
            'name': 'org name',
            'slug': 'org-name',
            'left_sequence': 1,
            'right_sequence': 2,
        }
        obj = objects.Organization.from_dict(values)
        res = self.driver.save(obj)

        api_mock.assert_called_once_with(mock.sentinel.session,
                                         values)
        model_mock.to_dict.assert_called_once_with()
        self.assertIsInstance(res, objects.Organization)
        self.assertEqual(mocks.UUID1, res.id.decode('utf8'))
        self.assertEqual(str(mocks.CREATED_ON), res.created_on)
        self.assertEqual('', res.parent_organization_id.decode('utf8'))
        self.assertEqual(mocks.UUID1, res.root_organization_id.decode('utf8'))
