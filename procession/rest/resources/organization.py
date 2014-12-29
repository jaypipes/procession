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

import falcon

from procession import exc
from procession import objects
from procession.rest import auth
from procession.rest import helpers
from procession.rest.resources import base
from procession import search


class OrganizationsResource(base.Resource):
    """
    REST resource for a collection of organizations in Procession API
    """
    @staticmethod
    def _handle_400(resp, err):
        msg = "Bad input provided for new organization: {0}"
        msg = msg.format(err)
        resp.body = msg
        resp.status = falcon.HTTP_400

    @auth.auth_required
    def on_get(self, req, resp):
        search_spec = search.SearchSpec.from_http_req(req)
        objs = objects.Organization.get_many(search_spec)
        resp.body = helpers.serialize(req, objs)
        resp.status = falcon.HTTP_200

    @auth.auth_required
    def on_post(self, req, resp):
        try:
            obj = objects.Organization.from_http_req(req)
            obj.save()
            resp.body = helpers.serialize(req, obj)
            resp.status = falcon.HTTP_201
            resp.location = "/organizations/{0}".format(obj.id)
        except exc.BadInput as e:
            self._handle_400(resp, e)


class OrganizationResource(base.Resource):
    """
    REST resource for a single organization in Procession API
    """
    @staticmethod
    def _handle_404(resp, org_id):
        msg = "An organization with ID or slug {0} could not be found."
        msg = msg.format(org_id)
        resp.body = msg
        resp.status = falcon.HTTP_404

    @auth.auth_required
    def on_get(self, req, resp, org_id):
        try:
            obj = objects.Organization.get_by_slug_or_key(req, org_id)
            resp.body = helpers.serialize(req, obj)
            resp.status = falcon.HTTP_200
        except exc.NotFound:
            self._handle_404(resp, org_id)

    @auth.auth_required
    def on_delete(self, req, resp, org_id):
        try:
            obj = objects.Organization.get_by_slug_or_key(req, org_id)
            obj.remove()
            resp.status = falcon.HTTP_204
        except exc.NotFound:
            self._handle_404(resp, org_id)


class OrgGroupsResource(base.Resource):
    """
    REST resource for a collection of groups for a single root
    organization in Procession API. This simply implements a shortcut
    route translation for:

    GET /groups?rootOrganizationId={org_id}
    to
    GET /organizations/{org_id}/groups
    """
    @auth.auth_required
    def on_get(self, req, resp, org_id):
        search_spec = search.SearchSpec.from_http_req(req)
        search_spec.filter_by(rootOrganizationId=org_id)
        groups = objects.Group.get_many(search_spec)
        resp.body = helpers.serialize(req, groups)
        resp.status = falcon.HTTP_200

    @auth.auth_required
    def on_post(self, req, resp, org_id):
        try:
            group = objects.Group.from_http_req(req, rootOrganizationId=org_id)
            group.save()
            resp.body = helpers.serialize(req, group)
            resp.status = falcon.HTTP_201
            resp.location = "/organization/{0}/groups/{1}".format(org_id, group.id)
        except exc.NotFound:
            msg = "An organization with ID or slug {0} could not be found."
            msg = msg.format(org_id)
            resp.body = msg
            resp.status = falcon.HTTP_404
        except exc.BadInput as e:
            resp.body = "Bad input: {0}".format(e)
            resp.status = falcon.HTTP_400
