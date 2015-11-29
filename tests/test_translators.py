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
                              tzinfo=translators._UTC),
            datetime.datetime(2015, 1, 23, 10, 36, 22),
            '2015-01-23T10:36:22Z',
            '2015-01-23T10:36:22',
            '2015-01-23T10:36:22+00:00',
            '2015-01-23T10:36:22-00:00',
            1422009382,
            1422009382.00,
        ]
        expected = six.text_type('2015-01-23T10:36:22+00:00')
        for subject in subjects:
            res = translators.coerce_iso8601_string(subject)
            msg = "Failed to coerce %r to %r. Got %r instead."
            msg = msg % (subject, expected, res)
            self.assertEqual(expected, res, msg)

    def test_coerce_iso8601_string_failure(self):
        subjects = [
            '123',
            object,
            [],
            {},
            '2015-01-23F10:36:22-00:00',
        ]
        for subject in subjects:
            with testtools.ExpectedException(ValueError):
                translators.coerce_iso8601_string(subject)

    def test_coerce_datetime_success(self):
        subjects = [
            datetime.datetime(2015, 1, 23, 10, 36, 22,
                              tzinfo=translators._UTC),
            datetime.datetime(2015, 1, 23, 10, 36, 22),
            '2015-01-23T10:36:22Z',
            '2015-01-23T10:36:22',
            '2015-01-23T10:36:22+00:00',
            '2015-01-23T10:36:22-00:00',
            1422009382,
            1422009382.00,
        ]
        expected = datetime.datetime(2015, 1, 23, 10, 36, 22,
                                     tzinfo=translators._UTC)
        for subject in subjects:
            res = translators.coerce_datetime(subject)
            msg = "Failed to coerce %r to %r. Got %r instead."
            msg = msg % (subject, expected, res)
            self.assertEqual(expected, res, msg)

    def test_coerce_datetime_failure(self):
        subjects = [
            '123',
            object,
            [],
            {},
        ]
        for subject in subjects:
            with testtools.ExpectedException(ValueError):
                translators.coerce_datetime(subject)

    def test_coerce_nullstring_to_none_success(self):
        subjects = [
            '',
            six.b(''),
        ]
        for subject in subjects:
            res = translators.coerce_nullstring_to_none(subject)
            self.assertIsNone(res)

        subjects = [
            'this',
            six.b('this'),
        ]
        expected = [
            'this',
            six.b('this'),
        ]
        for subject, expected in zip(subjects, expected):
            res = translators.coerce_nullstring_to_none(subject)
            msg = "Failed to coerce %r to %r. Got %r instead."
            msg = msg % (subject, expected, res)
            self.assertEqual(expected, res, msg)

    def test_coerce_nullstring_to_none_failure(self):
        subjects = [
            123,
            0,
            456.78,
            object,
            [],
            {}
        ]
        for subject in subjects:
            with testtools.ExpectedException(ValueError):
                translators.coerce_nullstring_to_none(subject)

    def test_coerce_none_to_nullstring_success(self):
        subjects = [
            None,
        ]
        for subject in subjects:
            res = translators.coerce_none_to_nullstring(subject)
            self.assertEqual(six.text_type(''), res)

        subjects = [
            'this',
            six.b('this'),
        ]
        expected = [
            'this',
            six.b('this'),
        ]
        for subject, expected in zip(subjects, expected):
            res = translators.coerce_none_to_nullstring(subject)
            msg = "Failed to coerce %r to %r. Got %r instead."
            msg = msg % (subject, expected, res)
            self.assertEqual(expected, res, msg)

    def test_coerce_none_to_nullstring_failure(self):
        subjects = [
            123,
            0,
            456.78,
            object,
            [],
            {}
        ]
        for subject in subjects:
            with testtools.ExpectedException(ValueError):
                translators.coerce_none_to_nullstring(subject)
