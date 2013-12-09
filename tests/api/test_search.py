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
import mock
import testtools

from procession.api import search

from tests import base


class TestApiSearch(base.UnitTest):

    def test_search_spec_sort_order_bad_request(self):
        req = mock.Mock(spec=falcon.Request)
        req.get_param_as_int.return_value = 2
        req.get_param_as_list.side_effect = [
            ['created_on'],  # sort fields
            ['desc', 'asc'],  # sort directions
            []  # group by fields
        ]

        with testtools.ExpectedException(falcon.HTTPBadRequest):
            search.SearchSpec(req)

    def test_search_spec_sort_dir_missing_filled(self):
        req = mock.Mock(spec=falcon.Request)
        req.get_param_as_int.return_value = 2
        req.get_param_as_list.side_effect = [
            ['created_on'],  # sort fields
            [],  # sort directions
            []  # group by fields
        ]
        req._params = dict()

        spec = search.SearchSpec(req)
        self.assertEquals(['asc'], spec.sort_dir)

    def test_get_order_by(self):
        req = mock.Mock(spec=falcon.Request)
        req.get_param_as_int.return_value = 2
        req.get_param_as_list.side_effect = [
            ['created_on', 'name'],  # sort fields
            ['asc', 'desc'],  # sort directions
            []  # group by fields
        ]
        req._params = dict()

        spec = search.SearchSpec(req)
        self.assertEquals(["created_on asc", "name desc"], spec.get_order_by())

    def test_search_filters_no_special_fields(self):
        req = mock.Mock(spec=falcon.Request)
        req.get_param_as_int.return_value = 2
        req.get_param_as_list.side_effect = [
            [],  # sort fields
            [],  # sort directions
            []  # group by fields
        ]
        req._params = dict(sort_by="foo")

        spec = search.SearchSpec(req)
        self.assertEquals(dict(), spec.filters)
