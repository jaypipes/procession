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

from procession import exc
from procession.db import api as db_api
from procession.db import session as db_session
from procession.api import auth
from procession.api import context
from procession.api import helpers
from procession.api import search

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class VersionsResource(object):

    """
    Returns version discovery on root URL
    """

    def on_get(self, req, resp):
        ctx = context.from_request(req)  # NOQA
        versions = [
            {
                'major': '1',
                'minor': '0',
                'current': True
            }
        ]
        resp.body = helpers.serialize(req, versions)
        resp.status = falcon.HTTP_302


class UsersResource(object):

    """
    REST resource for a collection of users in Procession API
    """

    @auth.auth_required
    def on_get(self, req, resp):
        ctx = context.from_request(req)
        search_spec = search.SearchSpec(req)
        users = db_api.users_get(ctx, search_spec)
        resp.body = helpers.serialize(req, users)
        resp.status = falcon.HTTP_200

    @auth.auth_required
    def on_post(self, req, resp):
        ctx = context.from_request(req)
        to_add = helpers.deserialize(req)

        try:
            sess = db_session.get_session()
            user = db_api.user_create(ctx, to_add, session=sess)
            sess.commit()
            resp.body = helpers.serialize(req, user)
            resp.status = falcon.HTTP_201
            resp.location = "/users/{0}".format(user.id)
        except ValueError, e:
            raise falcon.HTTPError(falcon.HTTP_400, 'Bad Input', str(e))


class UserResource(object):

    """
    REST resource for a single user in Procession API
    """

    @auth.auth_required
    def on_get(self, req, resp, user_id):
        ctx = context.from_request(req)
        try:
            user = db_api.user_get_by_id(ctx, user_id)
            resp.body = helpers.serialize(req, user)
            resp.status = falcon.HTTP_200
        except exc.NotFound:
            msg = "A user with ID {0} could not be found.".format(user_id)
            resp.body = msg
            resp.status = falcon.HTTP_404

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
    app.set_default_route(VersionsResource())
