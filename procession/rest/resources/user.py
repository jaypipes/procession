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

import falcon

from procession import exc
from procession import objects
from procession.rest import auth
from procession.rest import helpers
from procession.rest.resources import base
from procession import search


class UsersResource(base.Resource):
    """
    REST resource for a collection of users in Procession API
    """
    @auth.auth_required
    def on_get(self, req, resp):
        search_spec = search.SearchSpec.from_http_req(req)
        objs = objects.User.get_many(search_spec)
        resp.body = helpers.serialize(req, objs)
        resp.status = falcon.HTTP_200

    @auth.auth_required
    def on_post(self, req, resp):
        try:
            obj = objects.User.from_http_req(req)
            obj.save()
            resp.body = helpers.serialize(req, obj)
            resp.status = falcon.HTTP_201
            resp.location = "/users/{0}".format(obj.id)
        except exc.BadInput as e:
            resp.body = "Bad input: {0}".format(e)
            resp.status = falcon.HTTP_400


class UserResource(base.Resource):
    """
    REST resource for a single user in Procession API
    """
    @staticmethod
    def _handle_404(resp, user_id):
        msg = "A user with ID or slug {0} could not be found."
        msg = msg.format(user_id)
        resp.body = msg
        resp.status = falcon.HTTP_404

    @staticmethod
    def _handle_400(resp, user_id, err):
        msg = "Bad input provided for update of user {0}: {1}"
        msg = msg.format(user_id, err)
        resp.body = msg
        resp.status = falcon.HTTP_400

    @auth.auth_required
    def on_get(self, req, resp, user_id):
        try:
            obj = objects.User.get_by_slug_or_key(req, user_id)
            resp.body = helpers.serialize(req, obj)
            resp.status = falcon.HTTP_200
        except exc.NotFound:
            self._handle_404(resp, user_id)

    @auth.auth_required
    def on_put(self, req, resp, user_id):
        try:
            obj = objects.User.from_http_req(req)
            obj.update()
            resp.body = helpers.serialize(req, obj)
            resp.status = falcon.HTTP_200
            resp.location = "/users/{0}".format(obj.id)
        except exc.BadInput as e:
            self._handle_400(resp, user_id, e)
        except exc.NotFound:
            self._handle_404(resp, user_id)

    @auth.auth_required
    def on_delete(self, req, resp, user_id):
        try:
            obj = objects.User.get_by_slug_or_key(req, user_id)
            obj.remove()
            resp.status = falcon.HTTP_204
        except exc.NotFound:
            self._handle_404(resp, user_id)


class UserKeysResource(base.Resource):
    """
    REST resource for a collection of public keys for a user in Procession API
    """
    @staticmethod
    def _handle_404(resp, user_id):
        msg = "A user with ID or slug {0} could not be found."
        msg = msg.format(user_id)
        resp.body = msg
        resp.status = falcon.HTTP_404

    @auth.auth_required
    def on_get(self, req, resp, user_id):
        try:
            user = objects.User.get_by_slug_or_key(req, user_id)
        except exc.NotFound:
            self._handle_404(resp, user_id)
            return
        keys = user.get_public_keys()
        resp.body = helpers.serialize(req, keys)
        resp.status = falcon.HTTP_200

    @auth.auth_required
    def on_post(self, req, resp, user_id):
        try:
            user = objects.User.get_by_slug_or_key(req, user_id)
        except exc.NotFound:
            self._handle_404(resp, user_id)
            return
        try:
            key = objects.UserPublicKey.from_http_req(req, userId=user.id)
            key.save()
            resp.body = helpers.serialize(req, key)
            resp.status = falcon.HTTP_201
            resp.location = "/users/{0}/keys/{1}".format(user.id, key.id)
        except exc.BadInput as e:
            resp.body = "Bad input: {0}".format(e)
            resp.status = falcon.HTTP_400


class UserKeyResource(base.Resource):
    """
    REST resource for a single user key in Procession API
    """
    @staticmethod
    def _handle_404_user(resp, user_id):
        msg = "A user with ID or slug {0} could not be found."
        msg = msg.format(user_id)
        resp.body = msg
        resp.status = falcon.HTTP_404

    @staticmethod
    def _handle_404(resp, user_id, fingerprint):
        msg = "A key with fingerprint {0} for user {1} could not be found."
        msg = msg.format(fingerprint, user_id)
        resp.body = msg
        resp.status = falcon.HTTP_404

    @auth.auth_required
    def on_get(self, req, resp, user_id, fingerprint):
        try:
            user = objects.User.get_by_slug_or_key(req, user_id)
        except exc.NotFound:
            self._handle_404_user(resp, user_id)
            return
        try:
            search_spec = search.SearchSpec.from_http_req(req)
            search_spec.filter_by(userId=user.id, fingerprint=fingerprint)
            key = objects.UserPublicKey.get_one(search_spec)
            resp.body = helpers.serialize(req, key)
            resp.status = falcon.HTTP_200
        except exc.NotFound:
            self._handle_404(resp, user_id, fingerprint)

    @auth.auth_required
    def on_delete(self, req, resp, user_id, fingerprint):
        try:
            user = objects.User.get_by_slug_or_key(req, user_id)
        except exc.NotFound:
            self._handle_404_user(resp, user_id)
            return
        try:
            search_spec = search.SearchSpec.from_http_req(req)
            search_spec.filter_by(userId=user.id, fingerprint=fingerprint)
            key = objects.UserPublicKey.get_one(search_spec)
            key.remove()
            resp.status = falcon.HTTP_204
        except exc.NotFound:
            self._handle_404(resp, user_id, fingerprint)


class UserGroupsResource(base.Resource):
    """
    REST resource handling a user's membership in organization groups
    in Procession API
    """
    @staticmethod
    def _handle_404(resp, user_id):
        msg = "A user with ID or slug {0} could not be found."
        msg = msg.format(user_id)
        resp.body = msg
        resp.status = falcon.HTTP_404

    @auth.auth_required
    def on_get(self, req, resp, user_id):
        try:
            user = objects.User.get_by_slug_or_key(req, user_id)
        except exc.NotFound:
            self._handle_404(resp, user_id)
            return
        try:
            groups = user.get_groups()
            resp.body = helpers.serialize(req, groups)
            resp.status = falcon.HTTP_200
        except exc.NotFound:
            self._handle_404(resp, user_id)


class UserGroupResource(base.Resource):
    """
    REST resource for a single user group membership in Procession API
    """
    @staticmethod
    def _handle_404_user(resp, user_id):
        msg = "A user with ID or slug {0} could not be found."
        msg = msg.format(user_id)
        resp.body = msg
        resp.status = falcon.HTTP_404

    @staticmethod
    def _handle_404_group(resp, group_id):
        msg = "A group with ID or slug {0} could not be found."
        msg = msg.format(group_id)
        resp.body = msg
        resp.status = falcon.HTTP_404

    @auth.auth_required
    def on_delete(self, req, resp, user_id, group_id):
        try:
            user = objects.User.get_by_slug_or_key(req, user_id)
        except exc.NotFound:
            self._handle_404_user(resp, user_id)
            return
        try:
            user.remove_from_group(group_id)
            resp.status = falcon.HTTP_204
        except exc.NotFound:
            self._handle_404_group(resp, group_id)

    @auth.auth_required
    def on_put(self, req, resp, user_id, group_id):
        try:
            user = objects.User.get_by_slug_or_key(req, user_id)
        except exc.NotFound:
            self._handle_404_user(resp, user_id)
            return
        try:
            user.add_to_group(group_id)
            resp.status = falcon.HTTP_204
            resp.location = "/users/{0}/groups/{1}".format(user.id, group_id)
        except exc.NotFound:
            self._handle_404_group(resp, group_id)
