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

from procession.rest import context

DEFAULT_LIMIT_RESULTS = 20


class SearchSpec(object):
    """
    Simple object that describes a search request against the API.
    """
    def __init__(self,
                 context,
                 limit=DEFAULT_LIMIT_RESULTS,
                 marker=None,
                 sort_by=None,
                 sort_dir=None,
                 group_by=None,
                 filters=None,
                 filter_ors=None,
                 with_relations=None,
                 ):
        self.ctx = context
        self.limit = limit
        self.marker = marker
        self.sort_by = sort_by or []
        self.sort_dir = sort_dir or []
        self.group_by = group_by or []
        self.filters = filters or {}
        self.filter_ors = filter_ors or {}
        self.with_relations = with_relations or []

    @classmethod
    def from_http_req(cls, req):
        """
        :param req: 'falcon.request.Request' object that is queried for
                    various attributes

        :raises `falcon.HTTPBadRequest` if sort by and sort dir lists are
                not same length.
        """
        ctx = context.from_http_req(req)
        limit = req.get_param_as_int('limit') or DEFAULT_LIMIT_RESULTS
        marker = req.get_param('marker')
        sort_by = req.get_param_as_list('sort_by') or list()
        sort_dir = req.get_param_as_list('sort_dir') or list()

        if len(sort_dir) > 0 and (
                len(sort_dir) != len(sort_by)):
            msg = ("If you supply sort_dir values, you must supply the same "
                   "number of values as sort_by values.")
            raise falcon.HTTPBadRequest('Bad Request', msg)
        elif sort_by and not sort_dir:
            sort_dir = ["asc" for f in sort_by]

        group_by = req.get_param_as_list('group_by') or list()

        filters = req._params.copy()
        for name in ('limit', 'marker', 'sort_by', 'sort_dir', 'group_by'):
            if name in filters:
                del filters[name]
        return cls(ctx,
                   limit=limit,
                   marker=marker,
                   sort_by=sort_by,
                   sort_dir=sort_dir,
                   group_by=group_by,
                   filters=filters)

    def filter_or(self, **filters):
        """
        Override/set any OR-based filters for the query.
        """
        self.filter_ors.update(filters)
        return self

    def filter_by(self, **filters):
        """
        Override/set any AND-based filters for the query.
        """
        self.filters.update(filters)
        return self

    def with_relations(self, *relations):
        """
        Include in the search result the supplied relations.

        :param *relations: Iterable of `procession.object.Object` subclasses
                           that inform the user of the search spec what
                           related objects to retrieve.
        """
        self.with_relations = relations
        return self

    def get_order_by(self):
        """
        Returns a list of "$FIELD $DIR" strings
        """
        return ["{0} {1}".format(f, d)
                for f, d in zip(self.sort_by, self.sort_dir)]
