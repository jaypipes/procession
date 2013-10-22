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
import fixtures
import mock
import testtools

from procession.api import search


class TestApiSearch(testtools.TestCase):

    def setUp(self):
        self.useFixture(fixtures.FakeLogger())
        super(TestApiSearch, self).setUp()

    def test_search_spec_sort_order_bad_request(self):
        req = mock.Mock(spec=falcon.Request)
        req.get_param_as_int.return_value = 2
        req.get_param_as_list.side_effect = [
            ['created_on'],
            ['desc', 'asc']
        ]

        with testtools.ExpectedException(falcon.HTTPBadRequest):
            search.SearchSpec(req)
