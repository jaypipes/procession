# -*- encoding: utf-8 -*-
#
# Copyright 2015 Jay Pipes
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

"""Matchers used with the testtools.assertThat match framework"""

import mock
import pprint


class SearchSpecMismatch(object):

    def __init__(self, attr, expected, actual):
        self.attr = attr
        self.expected = expected
        self.actual = actual

    def describe(self):
        msg = ("SearchSpec expected to match attribute {0} with value "
               "{1} but found {2}")
        msg = msg.format(self.attr, self.expected, self.actual)

    def get_details(self):
        return {}


class SearchSpecMatches(object):

    def __init__(self,
                 limit=None,
                 marker=None,
                 sort_by=None,
                 sort_dir=None,
                 group_by=None,
                 filters=None,
                 filter_ors=None,
                 with_relations=None,
                 ):
        self.limit = limit or mock.ANY
        self.marker = marker or mock.ANY
        self.sort_by = sort_by or mock.ANY
        self.sort_dir = sort_dir or mock.ANY
        self.group_by = group_by or mock.ANY
        self.filters = filters or mock.ANY
        self.filter_ors = filter_ors or mock.ANY
        self.with_relations = with_relations or mock.ANY

    def __str__(self):
        return 'SearchSpecMatches(%s)' % pprint.pformat(self.__dict__)

    def match(self, other):
        for attr in ('limit', 'marker', 'sort_by', 'sort_dir', 'group_by',
                     'filters', 'filter_ors', 'with_relations'):
            this_attr = getattr(self, attr)
            if this_attr != mock.ANY:
                other_attr = getattr(other, attr)
                if this_attr != other_attr:
                    return SearchSpecMismatch(attr, this_attr, other_attr)
