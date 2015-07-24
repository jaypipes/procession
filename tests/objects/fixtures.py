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

import datetime

from procession import objects


UUID1 = 'c52007d5-dbca-4897-a86a-51e800753dec'
UUID2 = '1c552546-73a6-445b-83e8-c07e1b5eaf10'
_FINGERPRINT1 = '43:51:43:a1:b5:fc:8b:b7:0a:3a:a9:b1:0f:66:73:a8'
_FINGERPRINT2 = '8a:37:66:f0:1b:9a:a3:a0:7b:b8:cf:5b:1a:34:15:34'
_CREATED_ON = str(datetime.datetime(2013, 4, 27, 2, 45, 2))

ORGANIZATIONS = [
    objects.Organization.from_values(
        id=UUID1,
        name='Jets',
        slug='Jets',
        parent_organization_id='',
        root_organization_id='',
        created_on=_CREATED_ON
    ),
    objects.Organization.from_values(
        id=UUID2,
        name='Sharks',
        slug='sharks',
        parent_organization_id='',
        root_organization_id='',
        created_on=_CREATED_ON
    ),
]

USERS = [
    objects.User.from_values(
        id=UUID1,
        name='Albert Einstein',
        slug='albert-einstein',
        email='albert@emcsquared.com',
        created_on=_CREATED_ON,
    ),
    objects.User.from_values(
        id=UUID1,
        name='Charles Darwin',
        slug='charles-darwin',
        email='chuck@evolved.com',
        created_on=_CREATED_ON,
    ),
]

USER_PUBLIC_KEYS = [
    objects.UserPublicKey.from_values(
        user_id=UUID1,
        fingerprint=_FINGERPRINT1,
        public_key='emcsquared key',
        created_on=_CREATED_ON,
    ),
    objects.UserPublicKey.from_values(
        user_id=UUID2,
        fingerprint=_FINGERPRINT2,
        public_key='evolved key',
        created_on=_CREATED_ON,
    ),
]
