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

from procession import context
from procession import store

ENV_IDENTIFIER = 'procession.ctx'


def from_http_req(request):
    """
    Returns the `procession.context.Context` object that resides in the
    supplied `falcon.request.Request` WSGI environs. Sets the context
    object's store reference if not already there.

    :param request: `falcon.request.Request` object for the HTTP session.
    :param conf: `procession.config.Config` object reference from the
                 controller.
    """
    return request.env[ENV_IDENTIFIER]


def assure_context(req, resp, resource, params):
    """
    WSGI Pipeline hook intended to be placed before any API application
    that ensures a `procession.context.Context` object is in the WSGI
    request environs.
    """
    ctx = context.Context()
    ctx.store = store.Store(resource.conf)
    req.env[ENV_IDENTIFIER] = ctx
