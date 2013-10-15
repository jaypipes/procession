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
            api.user_delete(ctx, fakes.FAKE_UUID, session=self.sess)

    def test_user_update_not_found(self):
        ctx = mock.Mock()
        with testtools.ExpectedException(exc.NotFound):
            api.user_update(ctx, fakes.FAKE_UUID, {}, session=self.sess)

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

        foo_u = api.user_get(ctx, dict(email=user_info['email']),
                             session=self.sess)
        self.assertEquals(foo_u.display_name, user_info['display_name'])

        update_info = {
            'display_name': 'bar'
        }
        u = api.user_update(ctx, u.id, update_info, session=self.sess)
        self.assertEqual('bar', u.display_name)

        foo_u = api.user_get(ctx, dict(email=user_info['email']),
                             session=self.sess)
        self.assertEquals(foo_u.display_name, 'bar')

        api.user_delete(ctx, u.id, session=self.sess)

        with testtools.ExpectedException(exc.NotFound):
            api.user_delete(ctx, u.id, session=self.sess)

    def test_user_get_not_found(self):
        ctx = mock.Mock()
        with testtools.ExpectedException(exc.NotFound):
            api.user_get(ctx, dict(id=fakes.FAKE_UUID), session=self.sess)

    def test_user_get_by_id_not_found(self):
        ctx = mock.Mock()
        with testtools.ExpectedException(exc.NotFound):
            api.user_get_by_id(ctx, fakes.FAKE_UUID, session=self.sess)
