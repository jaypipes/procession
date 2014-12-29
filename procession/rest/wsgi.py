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

from procession import config
from procession import log
from procession.rest import context
from procession.rest.resources import domain
from procession.rest.resources import group 
from procession.rest.resources import organization
from procession.rest.resources import repository
from procession.rest.resources import user
from procession.rest.resources import version
from procession import store


def add_routes(app, conf):
    """
    Adds routes for all resources in the API to the supplied
    `falcon.API` WSGI application object

    :param app: `falcon.API` application object to add routes to
    :param conf: `procession.config.Config` object passed to all
                 of the resource controllers.
    """
    app.add_route('/organizations',
                  organization.OrganizationsResource(conf))
    app.add_route('/organizations/{org_id}',
                  organization.OrganizationResource(conf))
    app.add_route('/organizations/{org_id}/groups',
                  organization.OrgGroupsResource(conf))
    app.add_route('/groups',
                  group.GroupsResource(conf))
    app.add_route('/groups/{group_id}',
                  group.GroupResource(conf))
    app.add_route('/groups/{group_id}/users',
                  group.GroupUsersResource(conf))
    app.add_route('/users',
                  user.UsersResource(conf))
    app.add_route('/users/{user_id}',
                  user.UserResource(conf))
    app.add_route('/users/{user_id}/keys',
                  user.UserKeysResource(conf))
    app.add_route('/users/{user_id}/keys/{fingerprint}',
                  user.UserKeyResource(conf))
    app.add_route('/users/{user_id}/groups',
                  user.UserGroupsResource(conf))
    app.add_route('/users/{user_id}/groups/{group_id}',
                  user.UserGroupResource(conf))
    app.add_route('/domains',
                  domain.DomainsResource(conf))
    app.add_route('/domains/{domain_id}',
                  domain.DomainResource(conf))
    app.add_route('/domains/{domain_id}/repos',
                  domain.DomainRepositoriesResource(conf))
    app.add_route('/repos',
                  repository.RepositoriesResource(conf))
    app.add_route('/repos/{repo_id}',
                  repository.RepositoryResource(conf))
    app.add_route('/{domain}/{repo_name}',
                  domain.DomainRepositorySpecialResource(conf))
    app.add_route('/', version.VersionsResource(conf))


def wsgi_app(**options):
    """
    Returns a WSGI application that may be served in a container
    or web server

    :param **config: Configuration options for the app.
    """
    conf = config.init(**options)
    log.init(conf)
    store.Store(conf).init()
    app = falcon.API(before=[context.assure_context])
    add_routes(app, conf)
    return app
