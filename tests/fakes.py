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
import yaml

import mock

from procession.api import context
from procession.db import models


def get_search_spec(**kwargs):
    spec = mock.MagicMock()
    spec.filters = kwargs.get('filters', dict())
    spec.get_order_by.return_value = kwargs.get('order_by', list())
    spec.limit = kwargs.get('limit', 2)
    spec.marker = kwargs.get('marker')
    return spec


def _org_to_dict(self):
    return {
        'id': self.id,
        'display_name': self.display_name,
        'org_name': self.org_name,
        'slug': self.slug,
        'parent_organization_id': self.parent_organization_id,
        'root_organization_id': self.root_organization_id,
        'created_on': self.created_on
    }


def _user_to_dict(self):
    return {
        'id': self.id,
        'display_name': self.display_name,
        'user_name': self.user_name,
        'email': self.email,
        'slug': self.slug,
        'created_on': self.created_on,
    }


FAKE_UUID1 = 'c52007d5-dbca-4897-a86a-51e800753dec'
FAKE_UUID2 = '1c552546-73a6-445b-83e8-c07e1b5eaf10'
FAKE_FINGERPRINT1 = '43:51:43:a1:b5:fc:8b:b7:0a:3a:a9:b1:0f:66:73:a8'
FAKE_FINGERPRINT2 = '8a:37:66:f0:1b:9a:a3:a0:7b:b8:cf:5b:1a:34:15:34'

_m = mock.MagicMock()
_m.__class__ = models.Organization
_m.id = FAKE_UUID1
_m.display_name = 'Jets'
_m.org_name = 'jets'
_m.slug = 'sharks'
_m.parent_organization_id = None
_m.root_organization_id = FAKE_UUID1
_m.created_on = str(datetime.datetime(2013, 4, 27, 2, 45, 2))
_m.to_dict.return_value = _org_to_dict(_m)

FAKE_ORG1 = _m

_m = mock.MagicMock()
_m.__class__ = models.Organization
_m.id = FAKE_UUID2
_m.display_name = 'Sharks'
_m.org_name = 'sharks'
_m.slug = 'sharks'
_m.parent_organization_id = None
_m.root_organization_id = FAKE_UUID2
_m.created_on = str(datetime.datetime(2013, 4, 27, 2, 45, 2))
_m.to_dict.return_value = _org_to_dict(_m)

FAKE_ORG2 = _m

FAKE_ORGS = [
    FAKE_ORG1,
    FAKE_ORG2
]

_m = mock.MagicMock()
_m.__class__ = models.User
_m.id = FAKE_UUID1
_m.display_name = 'Albert Einstein'
_m.user_name = 'albert'
_m.slug = 'albert-einstein'
_m.email = 'albert@emcsquared.com'
_m.created_on = str(datetime.datetime(2013, 1, 17, 12, 30, 0))
_m.to_dict.return_value = _user_to_dict(_m)

FAKE_USER1 = _m
FAKE_USER1_JSON = json.dumps(_user_to_dict(_m))
FAKE_USER1_YAML = yaml.dump(_user_to_dict(_m))

_m = mock.MagicMock()
_m.__class__ = models.User
_m.id = FAKE_UUID2
_m.display_name = 'Charles Darwin'
_m.user_name = 'chuck'
_m.slug = 'charles-darwin'
_m.email = 'chuck@evolved.com'
_m.created_on = str(datetime.datetime(2013, 3, 11, 2, 23, 10))
_m.to_dict.return_value = _user_to_dict(_m)

FAKE_USER2 = _m
FAKE_USER2_JSON = json.dumps(_user_to_dict(_m))
FAKE_USER2_YAML = yaml.dump(_user_to_dict(_m))

FAKE_USERS = [
    FAKE_USER1,
    FAKE_USER2
]

FAKE_USERS_JSON = json.dumps([_user_to_dict(u) for u in FAKE_USERS])

_m = mock.MagicMock()
_m.__class__ = models.UserPublicKey
_m.user_id = FAKE_UUID1
_m.fingerprint = FAKE_FINGERPRINT1
_m.public_key = 'publickey1'
_m.created_on = str(datetime.datetime(2013, 3, 11, 2, 23, 10))
_m.deleted_on = None

FAKE_KEY1 = _m

_m = mock.MagicMock()
_m.__class__ = models.UserPublicKey
_m.user_id = FAKE_UUID2
_m.fingerprint = FAKE_FINGERPRINT2
_m.public_key = 'publickey2'
_m.created_on = str(datetime.datetime(2013, 3, 11, 2, 23, 10))
_m.deleted_on = None

FAKE_KEY2 = _m


class AuthenticatedContextMock(object):

    """
    Represents a `procession.api.context.Context` object for an
    authenticted identity.
    """

    def __init__(self, user_id=FAKE_USER1.id, roles=None):
        self.id = '67be7ab0-2715-414f-b0e9-10fe9e1499ac'
        self.authenticated = True
        self.user_id = user_id
        self.roles = roles or []


class AnonymousContextMock(object):

    """
    Represents a `procession.api.context.Context` object for an
    non-authenticted identity.
    """

    def __init__(self):
        self.id = '59496d65-5936-47a7-bc0a-b5fe2385a216'
        self.authenticated = False
        self.user_id = None
        self.roles = []


class RequestStub(object):

    def __init__(self):
        self._params = dict()
        self.content_type = 'application/json'

    def get_param_as_int(self, *args):
        pass

    def get_param_as_list(self, *args):
        pass

    def get_param(self, *args):
        pass


class AuthenticatedRequestMock(RequestStub):

    """
    Used in resource testing, where we don't care about HTTP header
    processing, serialization, authentication, etc. We only care about
    the context object that would be in the `falcon.request.Request`
    environs. This request mock contains a `procession.api.context.Context`
    object that represents a session for an authenticated identity.
    """

    def __init__(self, user_id=FAKE_USER1.id):
        assert user_id in [u.id for u in FAKE_USERS]
        self.context = AuthenticatedContextMock(user_id)
        self.env = {context._ENV_IDENTIFIER: self.context}
        super(AuthenticatedRequestMock, self).__init__()


class AnonymousRequestMock(RequestStub):

    """
    Used in resource testing, where we don't care about HTTP header
    processing, serialization, authentication, etc. We only care about
    the context object that would be in the `falcon.request.Request`
    environs. This request mock contains a `procession.api.context.Context`
    object that represents a session for a non-authenticated identity.
    """

    def __init__(self):
        self.context = AnonymousContextMock()
        self.env = {context._ENV_IDENTIFIER: self.context}
        super(AnonymousRequestMock, self).__init__()


class ResponseMock(object):

    """
    Used in resource testing, where we only care to examine
    the status and body attributes.
    """

    def __init__(self):
        self.status = None
        self.body = None

    def set_header(self, *args, **kwargs):
        pass
