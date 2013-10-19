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

import falcon
import falcon.testing as ftesting
import fixtures
import mock
import testtools

from procession import api
from oslo.config import cfg

from tests import fakes

CONF = cfg.CONF


class ApiTestBase(testtools.TestCase):

    def setUp(self):
        self.useFixture(fixtures.FakeLogger())
        self.resp_mock = ftesting.StartResponseMock()
        self.app = api.wsgi_app()
        super(ApiTestBase, self).setUp()

    def make_request(self, path, **kwargs):
        return self.app(ftesting.create_environ(path=path, **kwargs),
                        self.resp_mock)


class TestRootApi(ApiTestBase):

    def test_context_available(self):
        with mock.patch('procession.api.context.from_request') as mocked:
            self.assertFalse(mocked.called)
            self.make_request('/', method='GET')
            self.assertTrue(mocked.called)


class TestUsersApi(ApiTestBase):

    def test_users_delete_405(self):
        self.make_request('/users', method='DELETE')
        self.assertEquals(self.resp_mock.status, falcon.HTTP_405)

    def test_users_get(self):
        with mock.patch('procession.db.api.user_get') as mocked:
            mocked.return_value = fakes.FAKE_USERS
            response = self.make_request('/users', method='GET')
            self.assertEquals(self.resp_mock.status, falcon.HTTP_200)
            self.assertEquals(response[0], fakes.FAKE_USERS_JSON)
