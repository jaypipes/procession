# -*- encoding: utf-8 -*-
#
# Copyright 2014-2015 Jay Pipes
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
import six
import testtools

from procession import context
from procession import exc
from procession import objects
from procession.rest import context as rcontext
from procession import search

from tests import base
from tests import mocks
from tests import matchers


class TestObjects(base.UnitTest):

    def setUp(self):
        super(TestObjects, self).setUp()
        self.ctx = mock.MagicMock()

    def _get_request(self, **kwargs):
        env = helpers.create_environ(**kwargs)
        env[rcontext.ENV_IDENTIFIER] = self.ctx
        return falcon.Request(env)

    def test_has_changed_new_object(self):
        values = {
            'name': 'funky',
        }
        obj = objects.Organization.from_dict(values)
        self.assertTrue(obj.has_changed)

    def test_has_changed_existing_object(self):
        values = {
            'name': 'funky',
        }
        # Simulate a get_one() call, which ends up doing a from_dict()
        # and passing in the is_new=False parameter...
        obj = objects.Organization.from_dict(values, is_new=False)
        self.assertFalse(obj.has_changed)

        obj.name = 'monkey'
        self.assertTrue(obj.has_changed)

    def test_setattr_translator(self):
        values = {
            'name': 'funky',
            'parent_organization_id': mocks.UUID1
        }
        obj = objects.Organization.from_dict(values)
        self.assertIsNotNone(obj.parent_organization_id)

        # Test that setattr() runs translators from nullstring to None
        obj.parent_organization_id = ''
        self.assertIsNone(obj.parent_organization_id)

    def test_from_dict_to_dict(self):
        values = {
            'name': 'funky',
            'created_on': mocks.CREATED_ON,
        }
        obj = objects.Organization.from_dict(values)
        self.assertIsInstance(obj, objects.Organization)
        self.assertEqual(obj.name, 'funky')
        
        res = obj.to_dict()
        self.assertEqual('funky', res['name'])

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
            'name': 'My org'
        }
        req = self._get_request(method='POST', body=json.dumps(obj_dict))
        override_name = 'funky'
        obj = objects.Organization.from_http_req(req, name=override_name)
        # Verify that the kwarg overridden name is used for the organization
        # name and not the original in the request body.
        self.assertEqual(override_name, obj.name)

    def test_get_by_key_with_ctx(self):
        obj_dict = {
            'name': 'My org'
        }
        ctx = context.Context()
        ctx.store = mock.MagicMock()
        ctx.store.get_one.return_value = obj_dict

        obj = objects.Organization.get_by_key(ctx, mock.sentinel.key)
        expected_filters = {
            'id': mock.sentinel.key
        }
        search_match = matchers.SearchSpecMatches(filters=expected_filters)
        call_args = ctx.store.get_one.call_args[0]
        self.assertEqual(objects.Organization, call_args[0])
        self.assertThat(call_args[1], search_match)
        self.assertEqual('My org', obj.name)

    def test_get_by_key_with_http_req(self):
        # Almost the same as with manual context, but here we verify that
        # get_by_key() mines the http request's context object if passed.
        obj_dict = {
            'name': 'My org'
        }
        self.ctx.store = mock.MagicMock()
        self.ctx.store.get_one.return_value = obj_dict
        req = self._get_request(method='GET')

        obj = objects.Organization.get_by_key(req, mock.sentinel.key)
        expected_filters = {
            'id': mock.sentinel.key
        }
        search_match = matchers.SearchSpecMatches(filters=expected_filters)
        call_args = self.ctx.store.get_one.call_args[0]
        self.assertEqual(objects.Organization, call_args[0])
        self.assertThat(call_args[1], search_match)
        self.assertEqual('My org', obj.name)

    def test_get_by_slug_or_key_with_key(self):
        obj_dict = {
            'name': 'My org'
        }
        ctx = context.Context()
        ctx.store = mock.MagicMock()
        ctx.store.get_one.return_value = obj_dict

        obj = objects.Organization.get_by_slug_or_key(ctx, mocks.UUID1)
        expected_filters = {
            'id': mocks.UUID1
        }
        search_match = matchers.SearchSpecMatches(filters=expected_filters)
        call_args = ctx.store.get_one.call_args[0]
        self.assertEqual(objects.Organization, call_args[0])
        self.assertThat(call_args[1], search_match)
        self.assertEqual('My org', obj.name)

    def test_get_by_slug_or_key_with_slug(self):
        obj_dict = {
            'name': 'My org'
        }
        ctx = context.Context()
        ctx.store = mock.MagicMock()
        ctx.store.get_one.return_value = obj_dict

        obj = objects.Organization.get_by_slug_or_key(ctx, 'not-a-uuid')
        expected_filters = {
            'slug': 'not-a-uuid'
        }
        search_match = matchers.SearchSpecMatches(filters=expected_filters)
        call_args = ctx.store.get_one.call_args[0]
        self.assertEqual(objects.Organization, call_args[0])
        self.assertThat(call_args[1], search_match)
        self.assertEqual('My org', obj.name)

    def test_get_one(self):
        obj_dict = {
            'name': 'My org'
        }
        ctx = context.Context()
        ctx.store = mock.MagicMock()
        ctx.store.get_one.return_value = obj_dict

        search_spec = search.SearchSpec(ctx, filters=dict(name='My org'))
        obj = objects.Organization.get_one(search_spec)
        ctx.store.get_one.assert_called_once_with(objects.Organization,
                                                  search_spec)
        self.assertEqual('My org', obj.name)

    def test_get_many(self):
        obj_dict = {
            'name': 'My org'
        }
        ctx = context.Context()
        ctx.store = mock.MagicMock()
        ctx.store.get_many.return_value = [obj_dict]

        search_spec = search.SearchSpec(ctx, filters=dict(name='My org'))
        objs = objects.Organization.get_many(search_spec)
        ctx.store.get_many.assert_called_once_with(objects.Organization,
                                                  search_spec)
        self.assertEqual(1, len(objs))
        obj = objs[0]
        self.assertIsInstance(obj, objects.Organization)
        self.assertEqual('My org', obj.name)

    def test_add_relation(self):
        ctx = context.Context()
        ctx.store = mock.MagicMock()

        user_dict = {
            'id': mocks.UUID1,
            'name': 'My user'
        }
        user = objects.User.from_dict(user_dict, ctx=ctx)
        group_dict = {
            'id': mocks.UUID2,
            'name': 'My group'
        }
        group = objects.Group.from_dict(group_dict, ctx=ctx)

        user.add_relation(group)
        ctx.store.add_relation.assert_called_once_with(objects.User,
                                                       six.b(mocks.UUID1),
                                                       objects.Group,
                                                       six.b(mocks.UUID2))
