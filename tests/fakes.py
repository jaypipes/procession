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

import datetime
import json

import mock


def _user_to_dict(self):
    return {
        'id': self.id,
        'display_name': self.display_name,
        'email': self.email,
        'created_on': self.created_on,
        'deleted_on': self.deleted_on,
        'updated_on': self.updated_on
    }


FAKE_UUID1 = 'c52007d5-dbca-4897-a86a-51e800753dec'
FAKE_UUID2 = '1c552546-73a6-445b-83e8-c07e1b5eaf10'

_m = mock.MagicMock()
_m.id = FAKE_UUID1
_m.display_name = 'Albert Einstein'
_m.email = 'albert@emcsquared.com'
_m.created_on = str(datetime.datetime(2013, 1, 17, 12, 30, 0))
_m.deleted_on = None
_m.updated_on = str(datetime.datetime(2013, 1, 18, 10, 5, 4))
_m.to_dict.return_value = _user_to_dict(_m)

FAKE_USER1 = _m

_m = mock.MagicMock()
_m.id = FAKE_UUID2
_m.display_name = 'Charles Darwin'
_m.email = 'chuck@evolved.com'
_m.created_on = str(datetime.datetime(2013, 3, 11, 2, 23, 10))
_m.deleted_on = None
_m.updated_on = str(datetime.datetime(2013, 4, 2, 20, 1, 9))
_m.to_dict.return_value = _user_to_dict(_m)

FAKE_USER2 = _m

FAKE_USERS = [
    FAKE_USER1,
    FAKE_USER2
]


FAKE_USERS_JSON = json.dumps([_user_to_dict(u) for u in FAKE_USERS])
