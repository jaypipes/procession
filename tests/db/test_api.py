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

import fixtures
import mock
import testtools
from testtools import matchers

from procession import exc
from procession.db import api
from procession.db import session

from tests import fakes


class TestDbApi(testtools.TestCase):

    def setUp(self):
        self.useFixture(fixtures.FakeLogger())
        self.sess = session.get_session()
        super(TestDbApi, self).setUp()

    def test_user_create_bad_data(self):
        ctx = mock.Mock()
        user_info = {}
        with testtools.ExpectedException(ValueError):
            api.user_create(ctx, user_info)

    def test_user_update_bad_data(self):
        ctx = mock.Mock()
        user_info = {
            'display_name': 'foo',
            'email': 'foo@example.com'
        }
        u = api.user_create(ctx, user_info, session=self.sess)
        self.assertIn(u, self.sess.new)

        # Need to commit otherwise User.id not set
        self.sess.commit()
        self.addCleanup(api.user_delete, ctx, u.id, session=self.sess)

        update_info = {
            'display_name': None
        }
        with testtools.ExpectedException(ValueError):
            api.user_update(ctx, u.id, update_info, session=self.sess)

    def test_user_delete_bad_input(self):
        ctx = mock.Mock()
        user_id = 'nonexisting'
        with testtools.ExpectedException(exc.BadInput):
            api.user_delete(ctx, user_id, session=self.sess)

    def test_user_update_bad_input(self):
        ctx = mock.Mock()
        user_id = 'nonexisting'
        with testtools.ExpectedException(exc.BadInput):
            api.user_update(ctx, user_id, {}, session=self.sess)

    def test_user_delete_not_found(self):
        ctx = mock.Mock()
        with testtools.ExpectedException(exc.NotFound):
            api.user_delete(ctx, fakes.FAKE_UUID1, session=self.sess)

    def test_user_update_not_found(self):
        ctx = mock.Mock()
        with testtools.ExpectedException(exc.NotFound):
            api.user_update(ctx, fakes.FAKE_UUID1, {}, session=self.sess)

    def test_user_crud(self):
        ctx = mock.Mock()
        user_info = {
            'display_name': 'foo',
            'email': 'foo@example.com'
        }
        u = api.user_create(ctx, user_info, session=self.sess)
        self.assertIn(u, self.sess.new)

        with testtools.ExpectedException(exc.Duplicate):
            u = api.user_create(ctx, user_info, session=self.sess)

        self.assertEquals(u.display_name, user_info['display_name'])

        update_info = {
            'display_name': 'bar'
        }
        u = api.user_update(ctx, u.id, update_info, session=self.sess)
        self.assertEquals('bar', u.display_name)

        api.user_delete(ctx, u.id, session=self.sess)

        with testtools.ExpectedException(exc.NotFound):
            api.user_delete(ctx, u.id, session=self.sess)

    def test_user_get_by_id_not_found(self):
        ctx = mock.Mock()
        with testtools.ExpectedException(exc.NotFound):
            api.user_get_by_id(ctx, fakes.FAKE_UUID1, session=self.sess)

    def test_users_get(self):
        ctx = mock.Mock()
        user_infos = [
            {
                'display_name': 'foo',
                'email': 'foo@example.com'
            },
            {
                'display_name': 'bar',
                'email': 'bar@example.com'
            },
        ]
        for user_info in user_infos:
            u = api.user_create(ctx, user_info, session=self.sess)

            # Need to commit otherwise User.id not set
            self.sess.commit()
            self.addCleanup(api.user_delete, ctx, u.id, session=self.sess)

        spec = fakes.get_search_spec(filters=dict(email='bar@example.com'))
        users = api.users_get(ctx, spec, session=self.sess)

        self.assertThat(users, matchers.HasLength(2))

    def test_get_many(self):
        sess = mock.MagicMock()
        query = mock.MagicMock()
        sess.query.return_value = query
        query.filter_by = mock.MagicMock()
        query.order_by = mock.MagicMock()
        query.limit = mock.MagicMock()
        query.all = mock.MagicMock()

        model = mock.MagicMock()
        model.get_default_order_by.return_value = [mock.sentinel.gdob]

        # Test of an empty search spec with just a limit value
        spec = mock.MagicMock()
        type(spec).filters = mock.PropertyMock(return_value=None)
        spec.get_order_by.return_value = list()
        type(spec).marker = mock.PropertyMock(return_value=None)
        type(spec).limit = mock.PropertyMock(return_value=2)

        api._get_many(sess, model, spec)
        self.assertFalse(query.filter_by.called)
        spec.get_order_by.assert_called_once_with()
        query.order_by.assert_called_once_with(mock.sentinel.gdob)
        query.limit.assert_called_once_with(2)
        query.all.assert_called_once_with()

        spec.reset_mock()
        query.reset_mock()
        model.reset_mock()

        # Test of a non-filtering search spec with an order by
        # on a pair of columns
        spec.get_order_by.return_value = ["a desc", "b asc"]

        api._get_many(sess, model, spec)
        query.order_by.assert_called_once_with("a desc", "b asc")
        self.assertFalse(model.default_order_by.called)

        spec.reset_mock()
        query.reset_mock()
        model.reset_mock()

        # Test of a filtering search spec
        filters = {
            'name': 'foo'
        }
        type(spec).filters = mock.PropertyMock(return_value=filters)

        api._get_many(sess, model, spec)
        query.filter_by.assert_called_once_with(name='foo')
