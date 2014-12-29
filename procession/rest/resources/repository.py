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
from procession.rest import context
from procession.rest import helpers
from procession.rest.resources import base
from procession import search


class RepositoriesResource(base.Resource):
    """
    REST resource for a collection of repositories in Procession API
    """
    @auth.auth_required
    def on_get(self, req, resp):
        search_spec = search.SearchSpec.from_http_req(req)
        objs = objects.Repository.get_many(search_spec)
        resp.body = helpers.serialize(req, objs)
        resp.status = falcon.HTTP_200

    @auth.auth_required
    def on_post(self, req, resp):
        try:
            obj = objects.Repository.from_http_req(req)
            obj.save()
            resp.body = helpers.serialize(req, obj)
            resp.status = falcon.HTTP_201
            resp.location = "/repositories/{0}".format(obj.id)
        except exc.BadInput as e:
            resp.body = "Bad input: {0}".format(e)
            resp.status = falcon.HTTP_400


class RepositoryResource(base.Resource):
    """
    REST resource for a single repo in Procession API
    """
    @staticmethod
    def _handle_404(resp, repo_id):
        msg = "A repo with ID or slug {0} could not be found."
        msg = msg.format(repo_id)
        resp.body = msg
        resp.status = falcon.HTTP_404

    @staticmethod
    def _handle_400(resp, repo_id, err):
        msg = "Bad input provided for update of repo {0}: {1}"
        msg = msg.format(repo_id, err)
        resp.body = msg
        resp.status = falcon.HTTP_400

    @auth.auth_required
    def on_get(self, req, resp, repo_id):
        try:
            obj = objects.Repository.get_by_slug_or_key(req, repo_id)
            resp.body = helpers.serialize(req, obj)
            resp.status = falcon.HTTP_200
        except exc.NotFound:
            self._handle_404(resp, repo_id)

    @auth.auth_required
    def on_put(self, req, resp, repo_id):
        try:
            obj = objects.Repository.from_http_req(req)
            obj.update()
            resp.body = helpers.serialize(req, obj)
            resp.status = falcon.HTTP_200
            resp.location = "/repos/{0}".format(obj.id)
        except exc.BadInput as e:
            self._handle_400(resp, repo_id, e)
        except exc.NotFound:
            self._handle_404(resp, repo_id)

    @auth.auth_required
    def on_delete(self, req, resp, repo_id):
        try:
            obj = objects.Repository.get_by_slug_or_key(req, repo_id)
            obj.remove()
            resp.status = falcon.HTTP_204
        except exc.NotFound:
            self._handle_404(resp, repo_id)
