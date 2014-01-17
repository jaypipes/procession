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

from procession import helpers

from tests import fakes
from tests import base


class TestHelpers(base.UnitTest):

    def test_is_like_uuid(self):
        bad_subjects = [
            '123',
            123,
            u'fred',
            12.9,
            [1, 2, 3],
            {'1': '2'}
        ]
        for subject in bad_subjects:
            self.assertFalse(helpers.is_like_uuid(subject))

        good_subjects = [
            fakes.FAKE_UUID1,
            fakes.FAKE_UUID2
        ]
        for subject in good_subjects:
            self.assertTrue(helpers.is_like_uuid(subject))
