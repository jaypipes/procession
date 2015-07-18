# -*- encoding: utf-8 -*-
#
# Copyright 2014 Jay Pipes
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

import falcon
from falcon.testing import helpers
import six
import testtools

from procession import exc
from procession import objects
from procession.rest import version as rversion

from tests import base


class TestOrganizations(base.UnitTest):

    @staticmethod
    def _get_request(**kwargs):
        env = helpers.create_environ(**kwargs)
        env['procession.ctx'] = 'ctx'
        return falcon.Request(env)

    def test_organization(self):
        obj = objects.Organization.from_values(name='funky')
        self.assertIsInstance(obj, objects.Object)
        self.assertEqual(obj.name, 'funky')

    def test_organization_rest_v1_0(self):
        version = "1.0"
        obj_dict = {
            # Missing required name attribute...
        }
        req = self._get_request(method='POST',
                                body=json.dumps(obj_dict),
                                headers={
                                    rversion.VERSION_HEADER: version
                                })
        with testtools.ExpectedException(exc.BadInput):
            objects.Organization.from_http_req(req)

        obj_dict = {
            'name': 'My org',
        }
        req = self._get_request(method='POST',
                                body=json.dumps(obj_dict),
                                headers={
                                    rversion.VERSION_HEADER: version
                                })
        obj = objects.Organization.from_http_req(req)
        self.assertEqual('My org', obj.name)
        self.assertEqual(six.b(''), obj.parentOrganizationId)
