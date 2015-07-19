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

import datetime
import json
import mock
import tempfile

import falcon
from falcon.testing import helpers
import testtools

from procession import context
from procession import exc
from procession import objects

from tests import base


class TestObjects(base.UnitTest):

    @staticmethod
    def _get_request(**kwargs):
        env = helpers.create_environ(**kwargs)
        env['procession.ctx'] = 'ctx'
        return falcon.Request(env)

    def test_from_dict(self):
        values = {
            'name': 'funky',
            'created_on': datetime.datetime.utcnow(),
        }
        obj = objects.Organization.from_dict(values)
        self.assertIsInstance(obj, objects.Organization)
        self.assertEqual(obj.name, 'funky')

    def test_from_values(self):
        obj = objects.Organization.from_values(name='funky')
        self.assertIsInstance(obj, objects.Organization)
        self.assertEqual(obj.name, 'funky')

    def test_from_capnp(self):
        org_capnp = objects.organization_capnp.Organization
        org_message = org_capnp.new_message(name='funky')
        with tempfile.NamedTemporaryFile() as msg_file:
            org_message.write(msg_file)
            obj = objects.Organization.from_capnp(open(msg_file.name, 'rb'))
        self.assertIsInstance(obj, objects.Organization)
        self.assertEqual(obj.name, 'funky')

    def test_from_http_req_400(self):
        obj_dict = {
            # Missing required name attribute...
        }
        req = self._get_request(method='POST', body=json.dumps(obj_dict))
        with testtools.ExpectedException(exc.BadInput):
            objects.Organization.from_http_req(req)

    def test_from_http_req(self):
        obj_dict = {
            'name': 'My org',
        }
        req = self._get_request(method='POST', body=json.dumps(obj_dict))
        obj = objects.Organization.from_http_req(req)
        self.assertEqual('My org', obj.name)

    def test_from_http_req_with_overrides(self):
        obj_dict = {
            'name': 'My org',
        }
        req = self._get_request(method='POST', body=json.dumps(obj_dict))
        obj = objects.Organization.from_http_req(req, name='funky')
        self.assertEqual('funky', obj.name)

    def test_get_by_key_with_ctx(self):
        obj_dict = {
            'name': 'My org',
        }
        ctx = context.Context()
        ctx.store = mock.MagicMock()
        ctx.store.get_one.return_value = obj_dict

        obj = objects.Organization.get_by_key(ctx, mock.sentinel.key)
        ctx.store.get_one.assert_called_once_with(ctx, mock.sentinel.key)
        self.assertEqual('funky', obj.name)
