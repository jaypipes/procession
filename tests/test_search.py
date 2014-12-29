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
from falcon.testing import helpers
import testtools

from procession import search

from tests import base


class TestApiSearch(base.UnitTest):

    @staticmethod
    def _get_request(**kwargs):
        env = helpers.create_environ(**kwargs)
        env['procession.ctx'] = 'ctx'
        return falcon.Request(env)

    def test_search_spec_sort_order_bad_request(self):
        qs = "sort_by=createdOn&sort_dir=desc&sort_dir=asc"
        req = self._get_request(query_string=qs)

        with testtools.ExpectedException(falcon.HTTPBadRequest):
            search.SearchSpec.from_http_req(req)

    def test_search_spec_sort_dir_missing_filled(self):
        qs = "sort_by=createdOn"
        req = self._get_request(query_string=qs)

        spec = search.SearchSpec.from_http_req(req)
        self.assertEquals(['asc'], spec.sort_dir)

    def test_get_order_by(self):
        qs = "sort_by=createdOn&sort_by=name&sort_dir=asc&sort_dir=desc"
        req = self._get_request(query_string=qs)

        spec = search.SearchSpec.from_http_req(req)
        self.assertEquals(["createdOn asc", "name desc"], spec.get_order_by())
