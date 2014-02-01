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


class OrganizationsResource(object):

    """
    REST resource for a collection of organizations in Procession API
    """

    @auth.auth_required
    def on_get(self, req, resp):
        ctx = context.from_request(req)
        search_spec = search.SearchSpec(req)
        orgs = db_api.organizations_get(ctx, search_spec)
        resp.body = helpers.serialize(req, orgs)
        resp.status = falcon.HTTP_200

    @auth.auth_required
    def on_post(self, req, resp):
        ctx = context.from_request(req)
        to_add = helpers.deserialize(req)

        try:
            sess = db_session.get_session()
            org = db_api.organization_create(ctx, to_add, session=sess)
            resp.body = helpers.serialize(req, org)
            resp.status = falcon.HTTP_201
            resp.location = "/organizations/{0}".format(org.id)
        except (exc.BadInput, ValueError, TypeError) as e:
            resp.body = "Bad input: {0}".format(e)
            resp.status = falcon.HTTP_400


class OrganizationResource(object):

    """
    REST resource for a single organization in Procession API
    """

    @auth.auth_required
    def on_get(self, req, resp, org_id):
        ctx = context.from_request(req)
        try:
            org = db_api.organization_get_by_pk(ctx, org_id)
            resp.body = helpers.serialize(req, org)
            resp.status = falcon.HTTP_200
        except exc.NotFound:
            msg = "A organization with ID {0} could not be found."
            msg = msg.format(org_id)
            resp.body = msg
            resp.status = falcon.HTTP_404

    @auth.auth_required
    def on_delete(self, req, resp, org_id):
        ctx = context.from_request(req)

        try:
            sess = db_session.get_session()
            db_api.organization_delete(ctx, org_id, session=sess)
            resp.status = falcon.HTTP_200
        except exc.NotFound:
            msg = "A organization with ID {0} could not be found."
            msg = msg.format(org_id)
            resp.body = msg
            resp.status = falcon.HTTP_404


class GroupsResource(object):

    """
    REST resource for a collection of groups in Procession API
    """

    @auth.auth_required
    def on_get(self, req, resp):
        ctx = context.from_request(req)
        search_spec = search.SearchSpec(req)
        groups = db_api.groups_get(ctx, search_spec)
        resp.body = helpers.serialize(req, groups)
        resp.status = falcon.HTTP_200

    @auth.auth_required
    def on_post(self, req, resp):
        ctx = context.from_request(req)
        to_add = helpers.deserialize(req)

        try:
            sess = db_session.get_session()
            group = db_api.group_create(ctx, to_add, session=sess)
            resp.body = helpers.serialize(req, group)
            resp.status = falcon.HTTP_201
            resp.location = "/groups/{0}".format(group.id)
        except (exc.BadInput, ValueError, TypeError) as e:
            resp.body = "Bad input: {0}".format(e)
            resp.status = falcon.HTTP_400


class GroupResource(object):

    """
    REST resource for a single group in Procession API
    """

    @auth.auth_required
    def on_get(self, req, resp, group_id):
        ctx = context.from_request(req)
        try:
            group = db_api.group_get_by_pk(ctx, group_id)
            resp.body = helpers.serialize(req, group)
            resp.status = falcon.HTTP_200
        except exc.NotFound:
            msg = "A group with ID {0} could not be found.".format(group_id)
            resp.body = msg
            resp.status = falcon.HTTP_404

    @auth.auth_required
    def on_put(self, req, resp, group_id):
        ctx = context.from_request(req)
        to_update = helpers.deserialize(req)

        try:
            sess = db_session.get_session()
            group = db_api.group_update(ctx, group_id, to_update,
                                        session=sess)
            resp.body = helpers.serialize(req, group)
            resp.status = falcon.HTTP_200
            resp.location = "/groups/{0}".format(group_id)
        except exc.NotFound:
            msg = "A group with ID {0} could not be found.".format(group_id)
            resp.body = msg
            resp.status = falcon.HTTP_404

    @auth.auth_required
    def on_delete(self, req, resp, group_id):
        ctx = context.from_request(req)

        try:
            sess = db_session.get_session()
            db_api.group_delete(ctx, group_id, session=sess)
            resp.status = falcon.HTTP_200
        except exc.NotFound:
            msg = "A group with ID {0} could not be found.".format(group_id)
            resp.body = msg
            resp.status = falcon.HTTP_404


class OrgGroupsResource(object):

    """
    REST resource for a collection of groups for a single root
    organization in Procession API. This simply implements a shortcut
    route translation for:

    GET /groups?root_organization_id={org_id}
    to
    GET /organizations/{org_id}/groups
    """

    @auth.auth_required
    def on_get(self, req, resp, org_id):
        ctx = context.from_request(req)
        search_spec = search.SearchSpec(req)
        search_spec.filters['root_organization_id'] = org_id
        groups = db_api.groups_get(ctx, search_spec)
        resp.body = helpers.serialize(req, groups)
        resp.status = falcon.HTTP_200

    @auth.auth_required
    def on_post(self, req, resp, org_id):
        ctx = context.from_request(req)
        to_add = helpers.deserialize(req)
        to_add['root_organization_id'] = org_id

        try:
            sess = db_session.get_session()
            group = db_api.group_create(ctx, to_add, session=sess)
            resp.body = helpers.serialize(req, group)
            resp.status = falcon.HTTP_201
            resp.location = "/groups/{0}".format(group.id)
        except (exc.BadInput, ValueError, TypeError) as e:
            resp.body = "Bad input: {0}".format(e)
            resp.status = falcon.HTTP_400


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
            resp.body = helpers.serialize(req, user)
            resp.status = falcon.HTTP_201
            resp.location = "/users/{0}".format(user.id)
        except (exc.BadInput, ValueError, TypeError) as e:
            resp.body = "Bad input: {0}".format(e)
            resp.status = falcon.HTTP_400


class UserResource(object):

    """
    REST resource for a single user in Procession API
    """

    @auth.auth_required
    def on_get(self, req, resp, user_id):
        ctx = context.from_request(req)
        try:
            user = db_api.user_get_by_pk(ctx, user_id)
            resp.body = helpers.serialize(req, user)
            resp.status = falcon.HTTP_200
        except exc.NotFound:
            msg = "A user with ID {0} could not be found.".format(user_id)
            resp.body = msg
            resp.status = falcon.HTTP_404

    @auth.auth_required
    def on_put(self, req, resp, user_id):
        ctx = context.from_request(req)
        to_update = helpers.deserialize(req)

        try:
            sess = db_session.get_session()
            user = db_api.user_update(ctx, user_id, to_update, session=sess)
            resp.body = helpers.serialize(req, user)
            resp.status = falcon.HTTP_200
            resp.location = "/users/{0}".format(user_id)
        except exc.NotFound:
            msg = "A user with ID {0} could not be found.".format(user_id)
            resp.body = msg
            resp.status = falcon.HTTP_404

    @auth.auth_required
    def on_delete(self, req, resp, user_id):
        ctx = context.from_request(req)

        try:
            sess = db_session.get_session()
            db_api.user_delete(ctx, user_id, session=sess)
            resp.status = falcon.HTTP_200
        except exc.NotFound:
            msg = "A user with ID {0} could not be found.".format(user_id)
            resp.body = msg
            resp.status = falcon.HTTP_404


class UserKeysResource(object):

    """
    REST resource for a collection of public keys for a user in Procession API
    """

    @auth.auth_required
    def on_get(self, req, resp, user_id):
        ctx = context.from_request(req)
        search_spec = search.SearchSpec(req)
        search_spec.filters['user_id'] = user_id
        keys = db_api.user_keys_get(ctx, search_spec)
        resp.body = helpers.serialize(req, keys)
        resp.status = falcon.HTTP_200

    @auth.auth_required
    def on_post(self, req, resp, user_id):
        ctx = context.from_request(req)
        to_add = helpers.deserialize(req)

        try:
            sess = db_session.get_session()
            key = db_api.user_key_create(ctx, user_id, to_add, session=sess)
            resp.body = helpers.serialize(req, key)
            resp.status = falcon.HTTP_201
            resp.location = "/users/{0}/keys/{1}".format(user_id, key.id)
        except exc.NotFound:
            msg = "A user with ID {0} could not be found.".format(user_id)
            resp.body = msg
            resp.status = falcon.HTTP_404
        except (exc.BadInput, ValueError) as e:
            resp.body = "Bad input: {0}".format(e)
            resp.status = falcon.HTTP_400


class UserKeyResource(object):

    """
    REST resource for a single user key in Procession API
    """

    @auth.auth_required
    def on_get(self, req, resp, user_id, fingerprint):
        ctx = context.from_request(req)
        try:
            key = db_api.user_key_get_by_pk(ctx, user_id, fingerprint)
            resp.body = helpers.serialize(req, key)
            resp.status = falcon.HTTP_200
        except exc.NotFound:
            msg = ("A key with fingerprint {0} for user {1} could not "
                   "be found.").format(fingerprint, user_id)
            resp.body = msg
            resp.status = falcon.HTTP_404

    @auth.auth_required
    def on_delete(self, req, resp, user_id, fingerprint):
        ctx = context.from_request(req)

        try:
            sess = db_session.get_session()
            db_api.user_key_delete(ctx, user_id, fingerprint, session=sess)
            resp.status = falcon.HTTP_200
        except exc.NotFound:
            msg = ("A key with fingerprint {0} for user {1} could not "
                   "be found.").format(fingerprint, user_id)
            resp.body = msg
            resp.status = falcon.HTTP_404


def add_routes(app):
    """
    Adds routes for all resources in the API to the supplied
    `falcon.API` WSGI application object

    :param app: `falcon.API` application object to add routes to
    """
    app.add_route('/organizations', OrganizationsResource())
    app.add_route('/organizations/{org_id}', OrganizationResource())
    app.add_route('/groups', GroupsResource())
    app.add_route('/groups/{group_id}', GroupResource())
    app.add_route('/organizations/{org_id}/groups', OrgGroupsResource())
    app.add_route('/users', UsersResource())
    app.add_route('/users/{user_id}', UserResource())
    app.add_route('/users/{user_id}/keys', UserKeysResource())
    app.add_route('/users/{user_id}/keys/{fingerprint}', UserKeyResource())
    app.add_route('/', VersionsResource())
