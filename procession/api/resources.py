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


class GroupUsersResource(object):

    """
    REST resource showing the users that are members of a group.
    """

    @auth.auth_required
    def on_get(self, req, resp, group_id):
        ctx = context.from_request(req)
        users = db_api.group_users_get(ctx, group_id)
        resp.body = helpers.serialize(req, users)
        resp.status = falcon.HTTP_200


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


class UserGroupsResource(object):

    """
    REST resource handling a user's membership in organization groups
    in Procession API
    """

    @auth.auth_required
    def on_get(self, req, resp, user_id):
        ctx = context.from_request(req)
        groups = db_api.user_groups_get(ctx, user_id)
        resp.body = helpers.serialize(req, groups)
        resp.status = falcon.HTTP_200


class UserGroupResource(object):

    """
    REST resource for a single user group membership in Procession API
    """

    @auth.auth_required
    def on_delete(self, req, resp, user_id, group_id):
        ctx = context.from_request(req)

        try:
            sess = db_session.get_session()
            db_api.user_group_remove(ctx, user_id, group_id, session=sess)
            resp.status = falcon.HTTP_200
        except exc.NotFound:
            msg = "A user with ID {0} could not be found.".format(user_id)
            resp.body = msg
            resp.status = falcon.HTTP_404
        except (exc.BadInput, ValueError) as e:
            resp.body = "Bad input: {0}".format(e)
            resp.status = falcon.HTTP_400

    @auth.auth_required
    def on_put(self, req, resp, user_id, group_id):
        ctx = context.from_request(req)
        try:
            sess = db_session.get_session()
            group = db_api.user_group_add(ctx, user_id, group_id,
                                          session=sess)
            resp.body = helpers.serialize(req, group)
            resp.status = falcon.HTTP_200
            resp.location = "/users/{0}/groups/{1}".format(user_id, group_id)
        except exc.NotFound:
            msg = ("A user with ID {0} or a group with ID {1} "
                   "could not be found.").format(user_id, group_id)
            resp.body = msg
            resp.status = falcon.HTTP_404
        except (exc.BadInput, ValueError) as e:
            resp.body = "Bad input: {0}".format(e)
            resp.status = falcon.HTTP_400


class DomainsResource(object):

    """
    REST resource for a collection of repository domains in Procession API
    """

    @auth.auth_required
    def on_get(self, req, resp):
        ctx = context.from_request(req)
        search_spec = search.SearchSpec(req)
        orgs = db_api.domains_get(ctx, search_spec)
        resp.body = helpers.serialize(req, orgs)
        resp.status = falcon.HTTP_200

    @auth.auth_required
    def on_post(self, req, resp):
        ctx = context.from_request(req)
        to_add = helpers.deserialize(req)

        try:
            sess = db_session.get_session()
            dom = db_api.domain_create(ctx, to_add, session=sess)
            resp.body = helpers.serialize(req, dom)
            resp.status = falcon.HTTP_201
            resp.location = "/domains/{0}".format(dom.id)
        except exc.NotFound as e:
            resp.body = "Not found: {0}".format(e)
            resp.status = falcon.HTTP_404
        except (exc.BadInput, ValueError, TypeError) as e:
            resp.body = "Bad input: {0}".format(e)
            resp.status = falcon.HTTP_400


class DomainResource(object):

    """
    REST resource for a single domain in Procession API
    """

    @auth.auth_required
    def on_get(self, req, resp, domain_id):
        ctx = context.from_request(req)
        try:
            domain = db_api.domain_get_by_pk(ctx, domain_id)
            resp.body = helpers.serialize(req, domain)
            resp.status = falcon.HTTP_200
        except exc.NotFound:
            msg = "A domain with ID {0} could not be found.".format(domain_id)
            resp.body = msg
            resp.status = falcon.HTTP_404

    @auth.auth_required
    def on_put(self, req, resp, domain_id):
        ctx = context.from_request(req)
        to_update = helpers.deserialize(req)

        try:
            sess = db_session.get_session()
            domain = db_api.domain_update(ctx, domain_id, to_update,
                                          session=sess)
            resp.body = helpers.serialize(req, domain)
            resp.status = falcon.HTTP_200
            resp.location = "/domains/{0}".format(domain_id)
        except exc.NotFound:
            msg = "A domain with ID {0} could not be found.".format(domain_id)
            resp.body = msg
            resp.status = falcon.HTTP_404

    @auth.auth_required
    def on_delete(self, req, resp, domain_id):
        ctx = context.from_request(req)

        try:
            sess = db_session.get_session()
            db_api.domain_delete(ctx, domain_id, session=sess)
            resp.status = falcon.HTTP_200
        except exc.NotFound:
            msg = "A domain with ID {0} could not be found.".format(domain_id)
            resp.body = msg
            resp.status = falcon.HTTP_404


class DomainRepositoriesResource(object):

    """
    REST resource for a collection of repositories for a single domain
    in Procession API
    """

    @auth.auth_required
    def on_get(self, req, resp, domain_id):
        try:
            ctx = context.from_request(req)
            search_spec = search.SearchSpec(req)
            repos = db_api.domain_repos_get(ctx, domain_id, search_spec)
            resp.body = helpers.serialize(req, repos)
            resp.status = falcon.HTTP_200
        except exc.NotFound:
            msg = "A domain with ID {0} could not be found.".format(domain_id)
            resp.body = msg
            resp.status = falcon.HTTP_404

    @auth.auth_required
    def on_post(self, req, resp, domain_id):
        ctx = context.from_request(req)
        to_add = helpers.deserialize(req)
        to_add['domain_id'] = domain_id

        try:
            sess = db_session.get_session()
            repo = db_api.repo_create(ctx, to_add, session=sess)
            resp.body = helpers.serialize(req, repo)
            resp.status = falcon.HTTP_201
            resp.location = "/repos/{0}".format(repo.id)
        except exc.NotFound as e:
            resp.body = "Not found: {0}".format(e)
            resp.status = falcon.HTTP_404
        except (exc.BadInput, ValueError, TypeError) as e:
            resp.body = "Bad input: {0}".format(e)
            resp.status = falcon.HTTP_400


class RepositoriesResource(object):

    """
    REST resource for a collection of repositories in Procession API
    """

    @auth.auth_required
    def on_get(self, req, resp):
        ctx = context.from_request(req)
        search_spec = search.SearchSpec(req)
        repos = db_api.repos_get(ctx, search_spec)
        resp.body = helpers.serialize(req, repos)
        resp.status = falcon.HTTP_200

    @auth.auth_required
    def on_post(self, req, resp):
        ctx = context.from_request(req)
        to_add = helpers.deserialize(req)

        try:
            sess = db_session.get_session()
            repo = db_api.repo_create(ctx, to_add, session=sess)
            resp.body = helpers.serialize(req, repo)
            resp.status = falcon.HTTP_201
            resp.location = "/repos/{0}".format(repo.id)
        except exc.NotFound as e:
            resp.body = "Not found: {0}".format(e)
            resp.status = falcon.HTTP_404
        except (exc.BadInput, ValueError, TypeError) as e:
            resp.body = "Bad input: {0}".format(e)
            resp.status = falcon.HTTP_400


class RepositoryResource(object):

    """
    REST resource for a single repo in Procession API
    """

    @auth.auth_required
    def on_get(self, req, resp, repo_id):
        ctx = context.from_request(req)
        try:
            repo = db_api.repo_get_by_pk(ctx, repo_id)
            resp.body = helpers.serialize(req, repo)
            resp.status = falcon.HTTP_200
        except exc.NotFound:
            msg = "A repo with ID {0} could not be found.".format(repo_id)
            resp.body = msg
            resp.status = falcon.HTTP_404

    @auth.auth_required
    def on_put(self, req, resp, repo_id):
        ctx = context.from_request(req)
        to_update = helpers.deserialize(req)

        try:
            sess = db_session.get_session()
            repo = db_api.repo_update(ctx, repo_id, to_update,
                                          session=sess)
            resp.body = helpers.serialize(req, repo)
            resp.status = falcon.HTTP_200
            resp.location = "/repos/{0}".format(repo_id)
        except exc.NotFound:
            msg = "A repo with ID {0} could not be found.".format(repo_id)
            resp.body = msg
            resp.status = falcon.HTTP_404
        except exc.BadInput as e:
            resp.body = "Bad input: {0}".format(e)
            resp.status = falcon.HTTP_400

    @auth.auth_required
    def on_delete(self, req, resp, repo_id):
        ctx = context.from_request(req)

        try:
            sess = db_session.get_session()
            db_api.repo_delete(ctx, repo_id, session=sess)
            resp.status = falcon.HTTP_200
        except exc.NotFound:
            msg = "A repo with ID {0} could not be found.".format(repo_id)
            resp.body = msg
            resp.status = falcon.HTTP_404
        except exc.BadInput as e:
            resp.body = "Bad input: {0}".format(e)
            resp.status = falcon.HTTP_400


class DomainRepositorySpecialResource(object):

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
    def on_get(self, req, resp, domain, repo_name):
        ctx = context.from_request(req)
        try:
            repo = db_api.domain_repo_get_by_name(ctx, domain, repo_name)
            resp.body = helpers.serialize(req, repo)
            resp.status = falcon.HTTP_200
        except exc.NotFound:
            msg = "Domain {0} could not be found.".format(domain)
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
    app.add_route('/organizations/{org_id}/groups', OrgGroupsResource())
    app.add_route('/groups', GroupsResource())
    app.add_route('/groups/{group_id}', GroupResource())
    app.add_route('/groups/{group_id}/users', GroupUsersResource())
    app.add_route('/users', UsersResource())
    app.add_route('/users/{user_id}', UserResource())
    app.add_route('/users/{user_id}/keys', UserKeysResource())
    app.add_route('/users/{user_id}/keys/{fingerprint}', UserKeyResource())
    app.add_route('/users/{user_id}/groups', UserGroupsResource())
    app.add_route('/users/{user_id}/groups/{group_id}', UserGroupResource())
    app.add_route('/domains', DomainsResource())
    app.add_route('/domains/{domain_id}', DomainResource())
    app.add_route('/domains/{domain_id}/repos', DomainRepositoriesResource())
    app.add_route('/repos', RepositoriesResource())
    app.add_route('/repos/{repo_id}', RepositoryResource())
    app.add_route('/{domain}/{repo_name}', DomainRepositorySpecialResource())
    app.add_route('/', VersionsResource())
