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

import mock

from procession.rest import version

from tests import base


class TestVersion(base.UnitTest):

    def test_to_tuple(self):
        values = [
            ((1, 2), (1, 2)),
            (('1.2'), (1, 2)),
        ]
        for value, expected in values:
            self.assertEqual(expected, version.to_tuple(value))

    def test_tuple_from_request(self):
        req = mock.MagicMock()
        req.get_header.return_value = "1.2"
        self.assertEqual((1, 2), version.tuple_from_request(req))
        req.get_header.assert_called_once_with(version.VERSION_HEADER)
