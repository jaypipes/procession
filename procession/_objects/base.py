# -*- encoding: utf-8 -*-
#
# Copyright 2015 Jay Pipes
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
Object API for the various resources exposed by Procession.

We use jsonschema to validate incoming REST API data, primarily in order to
avoid some repetitive validation try/except blocks in the API controller level.

We use a simplified versioning system that allows the API's version to evolve
over time and enables the controllers to receive and return information for a
range of possible API versions. This ensures we have a stable and
backwards-compatible API so that clients that understand an older version of
the Procession REST API can still communicate with more recent versions of a
Procession REST API server.
"""

import copy
import logging
import os

import jsonschema

from procession import context
from procession import exc
from procession import helpers
from procession import search
from procession import translators
from procession.rest import context as rest_context
from procession.rest import helpers as rest_helpers
from procession.rest import schemacatalog
from procession.rest import version

LOG = logging.getLogger(__name__)
SCHEMA_DIR = os.path.join(os.path.dirname(__file__), 'schemas')
JSONSCHEMA_CATALOG = schemacatalog.JSONSchemaCatalog()


class Object(object):
    """Base class for all objects used in Procession."""

    _SCHEMA = None
    """The `processon.objects.schema` object loaded for the object."""

    _SINGULAR_NAME = None
    """The singular name of the object, lowercased. e.g. organization."""

    _PLURAL_NAME = None
    """The pluralized name of the object, lowercased. e.g. organizations."""

    _FIELD_VALUE_TRANSLATORS = {}
    """
    Dict of names of any fields that should automatically have incoming values
    translated into some other type. The keys for the dict should be the field
    names. The values should be a translator functor from
    `procession.translators`
    """

    def __init__(self, is_new=True, **values):
        """
        Constructs a new object from a set of field key/value pairs.

        :param is_new: Optional boolean indicating whether the object is a new
                       object and has never been saved to backend storage.
        """
        self.__dict__['_is_new'] = is_new
        self.__dict__['_values'] = values
        self._SCHEMA.fieldnames if is_new else []
        self.__dict__['_changed_fields'] = set(schema_fields)

    @property
    def is_new(self):
        """
        Returns True if the object has never been saved to backing storage,
        False otherwise.
        """
        return self.__dict__['_is_new']

    @property
    def key(self):
        """
        Returns the key for the object. If there is more than one key field,
        a tuple is returned, otherwise a single variable of the type of field
        is returned.
        """
        key_Fields = self._SCHEMA.key_fields()
        if len(key_fields) == 1:
            return getattr(self.__dict__['_values'], key_fields[0])
        return tuple(getattr(self.__dict__['_values'], key)
                     for key in key_fields)

    @property
    def has_changed(self):
        """Returns True if the object has any unsaved changes."""
        return len(self.__dict__['_changed_fields']) > 0

    @property
    def changed_values(self):
        """
        Returns a dict of all field values that have changed since last save.
        """
        raw = {k: v for k, v in self.__dict__['_values'].items()
               if k in self.__dict__['_changed_fields']}
        return self.field_names_to_capnp(raw)

    def __setattr__(self, key, value):
        if key in self._FIELD_VALUE_TRANSLATORS:
            translator = self._FIELD_VALUE_TRANSLATORS[key]
            value = translator(value)
        # Mark this field as changed in our set() of changed keys
        self.__dict__['_changed_fields'].add(key)
        return setattr(self._message, key, value)

    def __getattr__(self, key):
        value = getattr(self.__dict__['_message'], key)
        if key in self._FIELD_VALUE_TRANSLATORS:
            translator = self._FIELD_VALUE_TRANSLATORS[key]
            reverser = getattr(translator, 'reverser')
            if callable(reverser):
                value = reverser(value)
        return value

    @classmethod
    def from_http_req(cls, req, **overrides):
        """
        Given a supplied dict or list coming from an HTTP API request
        body that has been deserialized), validate that properties of the list
        or dict match the JSONSchema for the HTTP method of the object, and
        return an appropriate object.

        :param req: The `falcon.request.Request` object.
        :param **overrides: Any attributes that should be overridden in the
                            serialized body. Useful for when we are dealing
                            with a collection resource's subcollection. For
                            example, when creating a new public key for a
                            user, the HTTP request looks like:

                                POST /users/{user_id}/keys

                            We override the value of the body's userId
                            field (if set) with the value of the {user_id}
                            from the URI itself.
        :returns An object of the appropriate subclass.
        :raises `exc.BadInput` if the object model's schema
                does not match the supplied instance structure or if the
                request could not be deserialized.
        """
        api_version = version.tuple_from_request(req)
        ctx = rest_context.from_http_req(req)
        deser_body = rest_helpers.deserialize(req)
        if overrides:
            deser_body.update(overrides)
        schema = JSONSCHEMA_CATALOG.schema_for_version(req.method,
                                                       cls._SINGULAR_NAME,
                                                       api_version)
        try:
            jsonschema.validate(deser_body, schema)
        except jsonschema.ValidationError as e:
            raise exc.BadInput(e)
        return cls(**values)

    @classmethod
    def from_values(cls, is_new=True, **values):
        """
        Constructs a new object from a set of field key/values and an optional
        `procession.context.Context` object. If the context object is None,
        then calling save(), update(), or remove() without supplying a context
        object will result in a `procession.exc.NoContext` exception being
        thrown.

        :param ctx: Optional `procession.context.Context` object.
        :param is_new: Optional boolean indicating whether the object is a new
                       object and has never been saved to backend storage.
        :param values: keyword arguments of attributes of the object to set.
        :returns An object of the appropriate subclass.
        """
        return cls.from_dict(values, is_new=is_new)

    @classmethod
    def from_dict(cls, subject, is_new=True):
        """
        Constructs a new object from a set of field key/values and an optional
        `procession.context.Context` object. If the context object is None,
        then calling save(), update(), or remove() without supplying a context
        object will result in a `procession.exc.NoContext` exception being
        thrown.

        :param subject: Python dict of attribute values to set on object.
        :param ctx: Optional `procession.context.Context` object.
        :param is_new: Optional boolean indicating whether the object is a new
                       object and has never been saved to backend storage.
        :returns An object of the appropriate subclass.
        """
        # Make sure we don't mess with any supplied parameters...
        subject_copy = copy.deepcopy(subject)
        for field, translator in cls._FIELD_VALUE_TRANSLATORS.items():
            if field in subject_copy:
                subject_copy[field] = translator(subject_copy[field])
        return cls(is_new=is_new, **subject_copy)

    @classmethod
    def get_by_key(cls, ctx_or_req, key, with_relations=None):
        """
        Returns a single object of this type that has a key matching the
        supplied value or values.

        :param ctx_or_req: Either a `falcon.request.Request` object or a
                           `procession.context.Context` object.
        :param key: single string key to look up in backend storage.
        :param with_relations: Optional list of object classes or class
                               strings representing the child relation
                               objects to include when retrieving the
                               parent record.
        :returns An object of the appropriate subclass.
        :raises `procession.exc.NotFound` if no such object found in backend
                storage.
        """
        ctx = cls._find_ctx(ctx_or_req)
        key_name = cls._KEY_FIELD
        filters = {
            key_name: key
        }
        search_spec = search.SearchSpec(ctx, filters=filters,
                                        relations=with_relations)
        data = ctx.store.get_one(cls, search_spec)

        # TODO(jaypipes): Implement ACLs here.
        return cls.from_dict(data, is_new=False)

    @classmethod
    def get_by_slug_or_key(cls, ctx_or_req, slug_or_key, with_relations=None):
        """
        Returns an object of the supplied type that has a key with
        the supplied string or a slug matching the supplied string.

        :param ctx_or_req: Either a `falcon.request.Request` object or a
                           `procession.context.Context` object.
        :param slug_or_key: A string that may be a slug or lookup key of the
                            object.
        :param with_relations: Optional list of object classes or class
                               strings representing the child relation
                               objects to include when retrieving the
                               parent record.
        :raises `procession.exc.NotFound` if no such object found in backend
                storage.
        """
        if helpers.is_like_uuid(slug_or_key):
            return cls.get_by_key(ctx_or_req, slug_or_key,
                                  with_relations=with_relations)
        else:
            ctx = cls._find_ctx(ctx_or_req)
            filters = {
                'slug': slug_or_key
            }
            search_spec = search.SearchSpec(ctx, filters=filters,
                                            relations=with_relations)
            data = ctx.store.get_one(cls, search_spec)

            # TODO(jaypipes): Implement ACLs here.
            return cls.from_dict(data, is_new=False)

    @classmethod
    def get_one(cls, search_spec):
        """
        Returns a single object of this type filtered using the supplied search
        spec. Raises `procession.exc.NotFound` if the object was not located in
        backend storage.

        :param search_spec: `procession.search.SearchSpec`
        :raises `procession.exc.NotFound` if no such object found in backend
                storage.
        """
        data = search_spec.ctx.store.get_one(cls, search_spec)
        # TODO(jaypipes): Implement ACLs here.
        return cls.from_dict(data, is_new=False)

    @classmethod
    def get_many(cls, search_spec):
        """
        Returns a list of objects of this type filtered, paged,
        and sorted using the supplied search spec.

        :param search_spec: `procession.search.SearchSpec`
        """
        # TODO(jaypipes): Implement ACLs here.
        data = search_spec.ctx.store.get_many(cls, search_spec)
        res = []
        for record in data:
            res.append(cls.from_dict(record, is_new=False))
        return res

    def to_dict(self):
        """
        Returns a Python dict of the fields in the object.

        :note The values will be converted from any storage-internal format to
              the appropriate expected native Python type for the field. For
              example, `datetime.datetime` objects would be returned for
              timestamp fields, which are might be stored as strings in backend
              storage.
        """
        raw = self.__dict__['_values']
        for field, translator in self._FIELD_VALUE_TRANSLATORS.items():
            reverser = getattr(translator, 'reverser')
            if field in raw and callable(reverser):
                raw[field] = reverser(raw[field])
        return raw

    def delete(self, ctx):
        """
        Removes the object from backend storage.

        :param ctx: `procession.context.Context` object.
        """
        pass

    def save(self, ctx):
        """
        Saves the object to backend storage.

        :param ctx: `procession.context.Context` object.
        """
        pass
