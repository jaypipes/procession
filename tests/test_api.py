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

import json
import yaml

import falcon
import falcon.testing as ftesting
import fixtures
import mock
import testtools
from testtools import matchers

from procession import api


class TestApi(testtools.TestCase):

    """
    This test case is testing the HTTP/WSGI aspects of the API endpoint,
    including HTTP error processing, serialization, and routing.

    note: This test is not intended to test the logic of the various API
    resources. Those tests are in test_api_resources.py.
    """

    def setUp(self):
        self.useFixture(fixtures.FakeLogger())
        self.resp_mock = ftesting.StartResponseMock()
        self.app = api.wsgi_app()
        super(TestApi, self).setUp()

    def make_request(self, path, **kwargs):
        return self.app(ftesting.create_environ(path=path, **kwargs),
                        self.resp_mock)

    def deserialize(self, path, in_format='json', **kwargs):
        """
        Helper method that calls make_request() and attempts to deserialize
        the body of the returned response.
        """
        ds_fn = {
            'json': json.loads,
            'yaml': yaml.load
        }
        body = self.make_request(path, **kwargs)[0]
        return ds_fn[in_format](body)

    def test_context_available(self):
        with mock.patch('procession.api.context.from_request') as mocked:
            self.assertFalse(mocked.called)
            self.make_request('/', method='GET')
            self.assertTrue(mocked.called)

    def test_versions_302(self):
        versions = self.deserialize('/', method='GET')
        self.assertEquals(self.resp_mock.status, falcon.HTTP_302)
        self.assertThat(versions, matchers.IsInstance(list))
        self.assertThat(len(versions), matchers.GreaterThan(0))
        self.assertThat(versions[0], matchers.IsInstance(dict))
        self.assertIn('current', versions[0].keys())
        self.assertThat([v for v in versions if v['current'] is True],
                        matchers.HasLength(1))

    def test_delete_405(self):
        self.make_request('/', method='DELETE')
        self.assertEquals(self.resp_mock.status, falcon.HTTP_405)
