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

import falcon
from oslo.config import cfg

from procession import log
from procession.api import context
from procession.api import resources
from procession.api import search

api_opts = [
    cfg.IntOpt('default_limit_results',
               default=search.DEFAULT_LIMIT_RESULTS,
               help='The number of results to limit results by, if not '
                    'specified.')
]

CONF = cfg.CONF
CONF.register_opts(api_opts, 'api')


def wsgi_app(**config):
    """
    Returns a WSGI application that may be served in a container
    or web server

    :param **config: Configuration options for the app.
    """
    log.setup(**config)
    app = falcon.API(before=[context.assure_context])
    resources.add_routes(app)
    return app
