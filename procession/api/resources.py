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

from oslo.config import cfg

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class UsersResource(object):

    """
    REST resource for a collection of users in Procession API
    """

    def on_get(self, req, resp):
        pass

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
