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

from procession import objects

from tests import fixtures

ORGANIZATIONS = [
    objects.Organization.from_values(
        id=fixtures.UUID1,
        name='Jets',
        slug='Jets',
        parent_organization_id='',
        root_organization_id='',
        created_on=fixtures.CREATED_ON
    ),
    objects.Organization.from_values(
        id=fixtures.UUID2,
        name='Sharks',
        slug='sharks',
        parent_organization_id='',
        root_organization_id='',
        created_on=fixtures.CREATED_ON
    ),
]

USERS = [
    objects.User.from_values(
        id=fixtures.UUID1,
        name='Albert Einstein',
        slug='albert-einstein',
        email='albert@emcsquared.com',
        created_on=fixtures.CREATED_ON,
    ),
    objects.User.from_values(
        id=fixtures.UUID1,
        name='Charles Darwin',
        slug='charles-darwin',
        email='chuck@evolved.com',
        created_on=fixtures.CREATED_ON,
    ),
]

USER_PUBLIC_KEYS = [
    objects.UserPublicKey.from_values(
        user_id=fixtures.UUID1,
        fingerprint=fixtures.FINGERPRINT1,
        public_key='emcsquared key',
        created_on=fixtures.CREATED_ON,
    ),
    objects.UserPublicKey.from_values(
        user_id=fixtures.UUID2,
        fingerprint=fixtures.FINGERPRINT2,
        public_key='evolved key',
        created_on=fixtures.CREATED_ON,
    ),
]
