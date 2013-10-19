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
import testtools

from procession.api import helpers

from tests import fakes


class TestApiHelpers(testtools.TestCase):

    def setUp(self):
        self.useFixture(fixtures.FakeLogger())
        super(TestApiHelpers, self).setUp()

    def test_serialize_dict(self):
        subject = dict()
        expected = '{}'
        results = helpers.serialize(subject)
        self.assertEquals(expected, results)

        subject = dict(this='that')
        expected = '{"this": "that"}'
        results = helpers.serialize(subject)
        self.assertEquals(expected, results)

        subject = fakes.FAKE_USER1
        expected = fakes.FAKE_USER1_JSON
        results = helpers.serialize(subject)
        self.assertEquals(expected, results)

    def test_serialize_list(self):
        subject = []
        expected = '[]'
        results = helpers.serialize(subject)
        self.assertEquals(expected, results)

        subject = [dict(this='that')]
        expected = '[{"this": "that"}]'
        results = helpers.serialize(subject)
        self.assertEquals(expected, results)

        subject = [fakes.FAKE_USER1, fakes.FAKE_USER2]
        expected = '[{0}, {1}]'.format(fakes.FAKE_USER1_JSON,
                                       fakes.FAKE_USER2_JSON)
        results = helpers.serialize(subject)
        self.assertEquals(expected, results)

    def test_serialize_dict_yaml(self):
        subject = dict()
        expected = '{}\n'
        results = helpers.serialize(subject, out_format='yaml')
        self.assertEquals(expected, results)

        subject = dict(this='that')
        expected = '{this: that}\n'
        results = helpers.serialize(subject, out_format='yaml')
        self.assertEquals(expected, results)

        subject = fakes.FAKE_USER1
        expected = fakes.FAKE_USER1_YAML
        results = helpers.serialize(subject, out_format='yaml')
        self.assertEquals(expected, results)

    def test_serialize_list_yaml(self):
        subject = []
        expected = '[]\n'
        results = helpers.serialize(subject, out_format='yaml')
        self.assertEquals(expected, results)

        subject = [dict(this='that')]
        expected = '- {this: that}\n'
        results = helpers.serialize(subject, out_format='yaml')
        self.assertEquals(expected, results)

        subject = [fakes.FAKE_USER1, fakes.FAKE_USER2]
        expected = '- {0}- {1}'.format(fakes.FAKE_USER1_YAML,
                                       fakes.FAKE_USER2_YAML)
        results = helpers.serialize(subject, out_format='yaml')
        self.assertEquals(expected, results)
