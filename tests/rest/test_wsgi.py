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

import falcon
import falcon.testing as ftesting
import mock

from procession.rest import wsgi

from tests import base


class TestApiWsgi(base.UnitTest):
    """
    This test case is testing the HTTP/WSGI aspects of the API endpoint,
    including HTTP error processing and routing.

    note: This test is not intended to test the logic of the various API
    resources. Those tests are in tests/rest/resources/.
    """
    def setUp(self):
        self.resp_mock = ftesting.StartResponseMock()
        self.app = wsgi.wsgi_app()
        super(TestApiWsgi, self).setUp()

    def make_request(self, path, **kwargs):
        return self.app(ftesting.create_environ(path=path, **kwargs),
                        self.resp_mock)

    @mock.patch('procession.rest.helpers.serialize')
    def test_versions_302(self, ser):
            self.make_request('/', method='GET')
            self.assertEquals(self.resp_mock.status, falcon.HTTP_302)
            self.assertTrue(ser.called)

    def test_delete_405(self):
        self.make_request('/', method='DELETE')
        self.assertEquals(self.resp_mock.status, falcon.HTTP_405)
