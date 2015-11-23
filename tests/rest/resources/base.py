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

import pprint

from testtools import content as ttcontent

from tests import fixtures
from tests import base


class ResourceTestCase(base.UnitTest):

    """
    This test case base class that stresses the logic of the various API
    resources. For HTTP/WSGI tests, see test_api.py.
    """

    def setUp(self):
        self.mocks = []
        self.resp = fixtures.ResponseMock()
        self.patch('procession.rest.helpers.serialize', lambda x, y: y)
        super(ResourceTestCase, self).setUp()

    def add_body_detail(self):
        formatted = pprint.pformat(self.resp.body, indent=2)
        self.addDetail('response-body', ttcontent.text_content(formatted))

    def as_anon(self, resource_method, *args, **kwargs):
        """
        Calls the supplied resource method, passing in a non-authenticated
        request object.
        """
        self.req = fixtures.AnonymousRequestMock()
        self.ctx = self.req.context
        resource_method(self.req, self.resp, *args, **kwargs)
        self.add_body_detail()

    def as_auth(self, resource_method, *args, **kwargs):
        """
        Calls the supplied resource method, passing in an authenticated
        request object.
        """
        self.req = fixtures.AuthenticatedRequestMock()
        self.ctx = self.req.context
        resource_method(self.req, self.resp, *args, **kwargs)
        self.add_body_detail()
