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

import logging

import falcon
from oslo.config import cfg

from procession.db import api as db_api
from procession.api import context
from procession.api import helpers as api_helpers

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class RootResource(object):

    """
    Returns version discovery on root URL
    """

    def on_get(self, req, resp):
        try:
            ctx = context.from_request(req)  # NOQA
            resp.body = "{'versions'}"
            resp.status = falcon.HTTP_200
        except Exception, e:
            resp.body = str(e)
            resp.status = falcon.HTTP_500


class UsersResource(object):

    """
    REST resource for a collection of users in Procession API
    """

    def on_get(self, req, resp):
        try:
            ctx = context.from_request(req)
            resp.body = api_helpers.serialize(db_api.user_get(ctx))
            resp.status = falcon.HTTP_200
        except Exception, e:
            resp.body = str(e)
            resp.status = falcon.HTTP_500

    def on_post(self, req, resp):
        pass


class UserResource(object):

    """
    REST resource for a single user in Procession API
    """

    def on_get(self, req, resp, user_id):
        pass

    def on_put(self, req, resp, user_id):
        pass

    def on_delete(self, req, resp, user_id):
        pass


def add_routes(app):
    """
    Adds routes for all resources in the API to the supplied
    `falcon.API` WSGI application object

    :param app: `falcon.API` application object to add routes to
    """
    app.add_route('/users', UsersResource())
    app.add_route('/users/{user_id}', UserResource())
    app.set_default_route(RootResource())
