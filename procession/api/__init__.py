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

from procession import config
from procession import db
from procession import log
from procession.api import context
from procession.api import resources
from procession.api import search


def wsgi_app(**options):
    """
    Returns a WSGI application that may be served in a container
    or web server

    :param **config: Configuration options for the app.
    """
    conf = config.init(**options)
    log.init(conf)
    db.init(conf)
    app = falcon.API(before=[context.assure_context])
    resources.add_routes(app)
    return app
