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
Stripped down object models for the various resources exposed by the
Procession API. We use jsonschema to validate these object models, to
avoid some repetitive validation try/except blocks on the database API
level. We also use a simplified versioning system in the objects in
order to provide for simple schema changes in a way that is upgradeable.
"""

import copy
import logging

import jsonpatch
import jsonschema

LOG = logging.getLogger(__name__)
UUID_REGEX_STRING = (r'^([0-9a-fA-F]){8}-*([0-9a-fA-F]){4}-*([0-9a-fA-F]){4}'
                     r'-*([0-9a-fA-F]){4}-*([0-9a-fA-F]){12}$')


class ObjectBase(object):

    """
    Base class that all objects in the object model derive from.
    """

    SCHEMA = None
    """The JSON-Schema object that describes the object's attributes"""

    def __init__(self, json_instance):
        """
        Given a supplied dict or list (typically coming in directly from an
        API request body that has been deserialized), construct an object
        and validate that properties of the list or dict match the schema
        of the object model.

        :raises `jsonschema.ValidationError` if the object model's schema
                does not match the supplied instance structure.
        """
        orig = copy.deepcopy(json_instance)
        object.__setattr__(self, '_data', orig)
        object.__setattr__(self, '_original', orig)
        jsonschema.validate(json_instance, self.SCHEMA)

    def patch(self):
        """
        Returns a JSON-Patch document representing any changes that have
        been made to the object since the object was initially constructed
        with the JSON instance.
        """
        return jsonpatch.make_patch(self._original, self._data)

    def __getattr__(self, key):
        """
        Simple translation of a object.attr getter to the underlying
        dict storage.

        :raises `KeyError` if key not in object's data dict
        """
        return self._data[key]

    def __setattr__(self, key, value):
        """
        Simple translation of a object.attr setter to the underlying
        dict storage, with a call to validate the newl-constructed
        data to the model's schema.

        :raises `jsonschema.ValidationError` if the object model's schema
                does not match the supplied instance attribute.
        :raises `KeyError` if key not in object's data dict

        :note On validation failure, value of key is reset to original
              value.
        """
        orig_value = self._data[key]
        data = self._data
        data[key] = value
        object.__setattr__(self, '_data', data)
        try:
            jsonschema.validate(self._data, self.SCHEMA)
        except jsonschema.ValidationError:
            data[key] = orig_value
            object.__setattr__(self, '_data', data)
            raise

    def __delattr__(self, key):
        """
        Simple translation of a object.attr setter to the underlying
        dict storage, with a call to validate the newl-constructed
        data to the model's schema.

        :raises `jsonschema.ValidationError` if the object model's schema
                does not validate after the deletion of the supplied key
        :raises `KeyError` if key not in object's data dict

        :note On validation failure, value of key is reset to original
              value.
        """
        orig_value = self._data
        del self._data[key]
        try:
            jsonschema.validate(self._data, self.SCHEMA)
        except jsonschema.ValidationError:
            self._data[key] = orig_value
            raise


class Organization(ObjectBase):

    SCHEMA = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "title": "A hierarchical container of zero or more other "
                 "organizations.",
        "additionalProperties": False,
        "properties": {
            "id": {
                "type": "string",
                "description": "UUID identifiers for the organization.",
                "pattern": UUID_REGEX_STRING
            },
            "display_name": {
                "type": "string",
                "description": "Name displayed for the organization.",
                "maxLength": 50,
            },
            "org_name": {
                "type": "string",
                "description": "Short name for the organization (used in "
                               "determining the organization's 'slug' value)",
                "maxLength": 30,
            },
            "slug": {
                "type": "string",
                "description": "Lowercased, hyphenated non-UUID identififer "
                               "used in URIs.",
                "maxLength": 100,
            },
            "created_on": {
                "type": "string",
                "description": "The datetime when the organization was "
                               "created, in ISO 8601 format.",
                "format": "datetime"
            },
            "root_organization_id": {
                "type": "string",
                "description": "The UUID of the root organization of the "
                               "organization tree that this organization "
                               "belongs to. Can be the same as the value "
                               "of this organization's id attribute.",
                "pattern": UUID_REGEX_STRING
            },
            "parent_organization_id": {
                "type": "string",
                "description": "The UUID of the immediate parent "
                               "organization of this organization "
                               "or null if this organization is a root "
                               "organization.",
                "pattern": UUID_REGEX_STRING
            }
        }
    }
