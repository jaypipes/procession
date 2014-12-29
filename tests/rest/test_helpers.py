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

from falcon import errors as fexc
import mock
import testtools

from procession.rest import helpers

from tests import base


class TestSerializers(base.UnitTest):

    def json_request(self, contents):
        req = mock.MagicMock(content_type='application/json')
        req.stream= mock.MagicMock()
        req.stream.read.return_value = contents
        return req

    def test_serialize_bad_mime_type(self):
        req = mock.MagicMock()
        req.client_prefers.return_value = None
        with testtools.ExpectedException(fexc.HTTPNotAcceptable):
            helpers.serialize(req, {})

    def test_deserialize_bad_mime_type(self):
        req = mock.MagicMock()
        req = mock.MagicMock(content_type='application/xml')
        with testtools.ExpectedException(fexc.HTTPNotAcceptable):
            helpers.deserialize(req)

    def test_serialize_dict(self):
        req = mock.MagicMock()
        req.client_prefers.return_value = 'application/json'
        subject = dict()
        expected = '{}'
        results = helpers.serialize(req, subject)
        self.assertEquals(expected, results)

        subject = dict(this='that')
        expected = '{"this": "that"}'
        results = helpers.serialize(req, subject)
        self.assertEquals(expected, results)

    def test_deserialize_dict(self):
        req = self.json_request('{}')
        expected = dict()
        results = helpers.deserialize(req)
        self.assertEquals(expected, results)

        expected = dict(this='that')
        req = self.json_request('{"this": "that"}')
        results = helpers.deserialize(req)
        self.assertEquals(expected, results)

    def test_serialize_list(self):
        req = mock.MagicMock()
        req.client_prefers.return_value = 'application/json'
        subject = []
        expected = '[]'
        results = helpers.serialize(req, subject)
        self.assertEquals(expected, results)

        subject = [dict(this='that')]
        expected = '[{"this": "that"}]'
        results = helpers.serialize(req, subject)
        self.assertEquals(expected, results)

    def test_serialize_dict_yaml(self):
        req = mock.MagicMock()
        req.client_prefers.return_value = 'application/yaml'
        subject = dict()
        expected = '{}\n'
        results = helpers.serialize(req, subject)
        self.assertEquals(expected, results)

        subject = dict(this='that')
        expected = '{this: that}\n'
        results = helpers.serialize(req, subject)
        self.assertEquals(expected, results)

    def test_serialize_list_yaml(self):
        req = mock.MagicMock()
        req.client_prefers.return_value = 'application/yaml'
        subject = []
        expected = '[]\n'
        results = helpers.serialize(req, subject)
        self.assertEquals(expected, results)

        subject = [dict(this='that')]
        expected = '- {this: that}\n'
        results = helpers.serialize(req, subject)
        self.assertEquals(expected, results)
