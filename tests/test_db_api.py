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

    def test_user_delete_bad_input(self):
        ctx = mock.Mock()
        user_id = 'nonexisting'
        with testtools.ExpectedException(exc.BadInput):
            api.user_delete(ctx, user_id)

    def test_user_delete_not_found(self):
        ctx = mock.Mock()
        with testtools.ExpectedException(exc.NotFound):
            api.user_delete(ctx, fakes.FAKE_UUID)

    def test_user_crud(self):
        ctx = mock.Mock()
        user_info = {
            'display_name': 'foo',
            'email': 'foo@example.com'
        }
        u = api.user_create(ctx, user_info, session=self.sess)
        self.assertIn(u, self.sess.new)

        self.sess.commit()

        with testtools.ExpectedException(exc.Duplicate):
            u = api.user_create(ctx, user_info, session=self.sess)

        api.user_delete(ctx, u.id, session=self.sess)

        with testtools.ExpectedException(exc.NotFound):
            api.user_delete(ctx, u.id, session=self.sess)
