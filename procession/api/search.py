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

DEFAULT_LIMIT_RESULTS = 20


class SearchSpec(object):

    """
    Simple object that describes a search request against the API.
    """

    def __init__(self, req):
        """
        :param req: 'falcon.request.Request' object that is queried for
                    various attributes

        :raises `falcon.HTTPBadRequest` if sort by and sort dir lists are
                not same length.
        """
        self.limit = req.get_param_as_int('limit') or DEFAULT_LIMIT_RESULTS
        self.marker = req.get_param('marker')
        self.sort_by = req.get_param_as_list('sort_by') or list()
        self.sort_dir = req.get_param_as_list('sort_dir') or list()

        if len(self.sort_dir) > 0 and (
                len(self.sort_dir) != len(self.sort_by)):
            msg = ("If you supply sort_dir values, you must supply the same "
                   "number of values as sort_by values.")
            raise falcon.HTTPBadRequest('Bad Request', msg)
        elif self.sort_by and not self.sort_dir:
            self.sort_dir = ["asc" for f in self.sort_by]

        self.group_by = req.get_param_as_list('group_by') or list()

        filters = req._params.copy()
        for name in ('limit', 'marker', 'sort_by', 'sort_dir', 'group_by'):
            if name in filters:
                del filters[name]

        self.filters = filters

    def get_order_by(self):
        """
        Returns a list of "$FIELD $DIR" strings
        """
        return ["{0} {1}".format(f, d)
                for f, d in zip(self.sort_by, self.sort_dir)]
