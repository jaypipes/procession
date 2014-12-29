# -*- encoding: utf-8 -*-
#
# Copyright 2013-2014 Jay Pipes
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

import functools

import falcon

from procession.rest import context

_AUTH_HEADER_TOKEN = 'x-auth-token'
_AUTH_HEADER_IDENTITY = 'x-auth-identity'
_AUTH_HEADER_KEY = 'x-auth-key'


def get_auth_uri():
    """
    Returns the URI of the authentication endpoint to get a
    token from.
    """
    pass


def is_valid_token(token, identity):
    """
    Validates a supplied token and identity against the authentication
    store. Returns True if the token and identity are valid, False
    otherwise.

    :param token: The token string
    :param identity: The identity string
    """
    return True


def authenticate(ctx, req):
    """
    This checks to see if there is an X-Auth-Token header in the request,
    and if so, authenticates the token with an authentication store. If
    no token is present, we look in the request for identity and key headers
    and attempt to use those to authenticate. Returns True if the token
    is valid or credentials are good, False otherwise.

    :param ctx: `procession.api.context.Context` object from WSGI environs
    :param req: `falcon.request.Request` object from WSGI pipeline
    """
    if ctx.authenticated is not None:
        return ctx.authenticated

    token = req.get_header(_AUTH_HEADER_TOKEN)
    identity = req.get_header(_AUTH_HEADER_IDENTITY)
    key = req.get_header(_AUTH_HEADER_KEY)
    if token is not None:
        return is_valid_token(token, identity)
    else:
        if identity is None or key is None:
            return False


def auth_required(fn):
    """
    Decorator for resource methods that require that the user is authenticated.
    This decorator sets the authenticated property of the request context if
    not set.

    :raises `falcon.HTTPUnauthorized` if validation fails
    """
    @functools.wraps(fn)
    def inner(resource, request, response, *args, **kwargs):
        ctx = context.from_http_req(request)
        ctx.authenticated = authenticate(ctx, request)
        if ctx.authenticated:
            return fn(resource, request, response, *args, **kwargs)
        msg = "Authentication failed."
        raise falcon.HTTPUnauthorized('Authentication required.',
                                      msg, scheme=get_auth_uri())
    return inner
