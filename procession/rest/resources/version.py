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

from procession.rest import helpers
from procession.rest.resources import base


class VersionsResource(base.Resource):

    """
    Returns version discovery on root URL
    """

    def on_get(self, req, resp):
        versions = [
            {
                'major': '1',
                'minor': '0',
                'current': True
            }
        ]
        resp.body = helpers.serialize(req, versions)
        resp.status = falcon.HTTP_302
