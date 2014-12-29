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


class DomainsResource(base.Resource):
    """
    REST resource for a collection of repository domains in Procession API
    """
    @auth.auth_required
    def on_get(self, req, resp):
        search_spec = search.SearchSpec.from_http_req(req)
        objs = objects.Domain.get_many(search_spec)
        resp.body = helpers.serialize(req, objs)
        resp.status = falcon.HTTP_200

    @auth.auth_required
    def on_post(self, req, resp):
        try:
            obj = objects.Domain.from_http_req(req)
            obj.save()
            resp.body = helpers.serialize(req, obj)
            resp.status = falcon.HTTP_201
            resp.location = "/domains/{0}".format(obj.id)
        except exc.BadInput as e:
            resp.body = "Bad input: {0}".format(e)
            resp.status = falcon.HTTP_400


class DomainResource(base.Resource):
    """
    REST resource for a single domain in Procession API
    """
    @staticmethod
    def _handle_404(resp, domain_id):
        msg = "A domain with ID or slug {0} could not be found."
        msg = msg.format(domain_id)
        resp.body = msg
        resp.status = falcon.HTTP_404

    @staticmethod
    def _handle_400(resp, domain_id, err):
        msg = "Bad input provided for update of domain {0}: {1}"
        msg = msg.format(domain_id, err)
        resp.body = msg
        resp.status = falcon.HTTP_400

    @auth.auth_required
    def on_get(self, req, resp, domain_id):
        try:
            obj = objects.Domain.get_by_slug_or_key(req, domain_id)
            resp.body = helpers.serialize(req, obj)
            resp.status = falcon.HTTP_200
        except exc.NotFound:
            self._handle_404(resp, domain_id)

    @auth.auth_required
    def on_put(self, req, resp, domain_id):
        try:
            obj = objects.Domain.from_http_req(req)
            obj.update()
            resp.body = helpers.serialize(req, obj)
            resp.status = falcon.HTTP_200
            resp.location = "/domains/{0}".format(obj.id)
        except exc.BadInput as e:
            self._handle_400(resp, domain_id, e)
        except exc.NotFound:
            self._handle_404(resp, domain_id)

    @auth.auth_required
    def on_delete(self, req, resp, domain_id):
        try:
            obj = objects.Domain.get_by_slug_or_key(req, domain_id)
            obj.remove()
            resp.status = falcon.HTTP_204
        except exc.NotFound:
            self._handle_404(resp, domain_id)


class DomainRepositoriesResource(base.Resource):
    """
    REST resource for a collection of repositories for a single domain
    in Procession API
    """
    @staticmethod
    def _handle_404(resp, domain_id):
        msg = "A domain with ID or slug {0} could not be found."
        msg = msg.format(domain_id)
        resp.body = msg
        resp.status = falcon.HTTP_404

    @auth.auth_required
    def on_get(self, req, resp, domain_id):
        try:
            domain = objects.Domain.get_by_slug_or_key(req, domain_id)
        except exc.NotFound:
            self._handle_404(resp, domain_id)
            return
        repos = domain.get_repos()
        resp.body = helpers.serialize(req, repos)
        resp.status = falcon.HTTP_200

    @auth.auth_required
    def on_post(self, req, resp, domain_id):
        try:
            domain = objects.Domain.get_by_slug_or_key(req, domain_id)
        except exc.NotFound:
            self._handle_404(resp, domain_id)
            return
        try:
            repo = objects.Repository.from_http_req(req, domainId=domain.id)
            repo.save()
            resp.body = helpers.serialize(req, repo)
            resp.status = falcon.HTTP_201
            resp.location = "/domains/{0}/repos/{1}".format(domain_id, repo.id)
        except exc.BadInput as e:
            resp.body = "Bad input: {0}".format(e)
            resp.status = falcon.HTTP_400


class DomainRepositorySpecialResource(base.Resource):
    """
    Special REST resource for being able to specify a repository in the
    Procession API using only slugs, names or identifiers for a domain and
    repository.

    This resource is routed next-to-last in the routing table (with the
    last route being the versions resource corresponding to the root /
    route).

    This allows the following to be routed to this resource:

    GET /jaypipes/procession

    The above would retrieve repository information about the repository
    named "procession" in the domain with a slug "jaypipes". Likewise this
    request:

    GET /procession/c52007d5-dbca-4897-a86a-51e800753dec

    would retrieve retrieve the repository information for the repository
    with ID c52007d5-dbca-4897-a86a-51e800753dec, but would raise a 404
    if there was no domain with the slug "procession" (or if the repository
    with ID c52007d5-dbca-4897-a86a-51e800753dec did not belong to the
    requestor or the requestor did not belong to a group with access to the
    domain with slug "procession")

    In this way, this "default route" works in a similar fashion to how
    GitHub's organizations, repositories and personal organizations work. If
    I go to https://github.com/jaypipes/procession, I get the Procession
    repository in the personal "jaypipes" organization (domain in Procession
    terminology). If I go to http://github.com/procession/procession, I get
    the Procession repository in the Procession organization (if I have access
    to that organization in GitHub...)
    """

    @auth.auth_required
    def on_get(self, req, resp, domain_id, repo_name):
        try:
            domain = objects.Domain.get_by_slug_or_key(req, domain_id)
        except exc.NotFound:
            msg = "A domain with ID or slug {0} could not be found."
            msg = msg.format(domain_id)
            resp.body = msg
            resp.status = falcon.HTTP_404
            return

        try:
            search_spec = search.SearchSpec.from_http_req(req)
            search_spec.filter_by(domainId=domain.id)
            search_spec.filter_or(name=repo_name, id=repo_name)
            repo = objects.Repository.get_one(search_spec)
            resp.body = helpers.serialize(req, repo)
            resp.status = falcon.HTTP_200
        except exc.NotFound:
            msg = "A repository with ID or name {0} could not be found."
            msg = msg.format(repo_name)
            resp.body = msg
            resp.status = falcon.HTTP_404
            return
