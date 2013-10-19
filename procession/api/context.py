# -*- mode: python -*-
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

import uuid

_ENV_IDENTIFIER = 'procession.ctx'


class Context(object):

    """
    An object that is created by the context WSGI middleware and stored
    in the `falcon.request.Request` object's env hash.
    """

    def __init__(self):
        self.authenticated = False
        self.id = uuid.uuid4()
        self.user_id = None


def from_request(request):
    """
    Returns the `procession.context.Context` object that resides in the
    supplied `falcon.request.Request` WSGI environs.
    """
    return request.env[_ENV_IDENTIFIER]


def assure_context(req, resp, params):
    """
    WSGI Pipeline hook intended to be placed before any API application
    that ensures a `procession.context.Context` object is in the WSGI
    request environs.
    """
    req.env[_ENV_IDENTIFIER] = Context()
