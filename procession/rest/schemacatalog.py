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

"""
The SCHEMA_DIR contains a number of JSONSchema documents for object types
managed by the Procession system. The naming of the schema documents follows
the pattern:

    $obj_type.[get|getmany|post|put]-$api_version.json

Where $obj_type is the lowercased_and_underscored name of the object type
that schema describes and $api_version is the REST API version that the schema
describes an object for.

For example, let us assume that in version 1.4 of the REST API, the schema for
"organization" object type added a new field to just the returned result of
the HTTP GET /organizations/{id} and HTTP GET /organizations API calls (but not
the schema of the expected body of the HTTP request for POST or PUT calls).

The SCHEMA_DIR might contain the following list of JSONSchema documents:

    SCHEMA_DIR/
        organization.get-1.0.json
        organization.get-1.4.json
        organization.getmany-1.0.json
        organization.getmany-1.4.json
        organization.post-1.0.json
        organization.put-1.0.json

In this way, we can search for a JSONSchema document to validate the particular
HTTP request that was sent to us, which may say it accepts an older version of
the REST API than the server is on.
"""

import collections
import json
import os

from procession.rest import version

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), '..', 'schemas')


def _get_jsonschema(obj_type, spec, version):
    schema_filename = "%s-%s-%s.json" % (obj_type, spec, version)
    path = os.path.join(SCHEMA_DIR, schema_filename)
    return json.loads(open(path, 'r+b').read())


class JSONSchemaCatalog(object):
    def __init__(self):
        self.obj_schemas = {}
        self.schema_cache = {}
        for filename in os.listdir(SCHEMA_DIR):
            if (not os.path.isfile(os.path.join(SCHEMA_DIR, filename)) or
                    not filename.endswith('.json')):
                continue
            filename = filename[:-5]  # Cut off the .json
            parts = filename.split('-')
            if not len(parts) == 3:
                print filename
                continue
            obj_type, method, ver_str = parts
            method = method.lower()
            ver = version.to_tuple(ver_str)
            if obj_type not in self.obj_schemas:
                self.obj_schemas[obj_type] = collections.defaultdict(set)
            self.obj_schemas[obj_type][method].add(ver)
            cache_key = (obj_type, method, ver)
            self.schema_cache[cache_key] = _get_jsonschema(obj_type, method,
                                                           ver_str)

    def schema_for_version(self, method, obj_type, ask_version):
        method = method.lower()
        min_matched = max([v for v in self.obj_schemas[obj_type][method]
                           if v <= ask_version])
        cache_key = (obj_type, method, min_matched)
        return self.schema_cache[cache_key]
