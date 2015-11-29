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

import datetime

import six
import testtools

from procession import translators

from tests import base


class TestTranslators(base.UnitTest):
    def test_coerce_iso8601_string_success(self):
        subjects = [
            datetime.datetime(2015, 1, 23, 10, 36, 22,
                              tzinfo=datetime.timezone.utc),
            datetime.datetime(2015, 1, 23, 10, 36, 22),
            '2015-01-23T10:36:22Z',
            '2015-01-23T10:36:22',
            '2015-01-23T10:36:22+00:00',
            '2015-01-23T10:36:22-00:00',
        ]
        expected = six.text_type('2015-01-23T10:36:22+00:00')
        for subject in subjects:
            res = translators.coerce_iso8601_string(subject)
            msg = "Failed to coerce %r to %r. Got %r instead."
            msg = msg % (subject, expected, res)
            self.assertEqual(expected, res, msg)

    def test_coerce_iso8601_string_failure(self):
        subjects = [
            '123'
        ]
        for subject in subjects:
            with testtools.ExpectedException(ValueError):
                translators.coerce_iso8601_string(subject)
