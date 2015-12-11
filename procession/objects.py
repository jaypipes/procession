# -*- encoding: utf-8 -*-
#
# Copyright 2014-2015 Jay Pipes
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
Stripped down object model API for the various resources exposed by
Procession.

We use Cap'N'Proto messages for the raw data exchange format inside of the
Procession services. This gives us a great, easy way to evolve the schema of
objects used in the system over time, a way to do a rolling upgrade of worker
services in the system, and a fast interchange and RPC format.

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

import capnp
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

# Tell Cap'N'P not to try to auto-find capnp files. We already know
# where they are...
capnp.remove_import_hook()

LOG = logging.getLogger(__name__)
SCHEMA_DIR = os.path.join(os.path.dirname(__file__), 'schemas')
JSONSCHEMA_CATALOG = schemacatalog.JSONSchemaCatalog()


def _capnp_schema_file(obj_type):
    return os.path.join(SCHEMA_DIR, obj_type + '.capnp')


organization_capnp = capnp.load(_capnp_schema_file('organization'))
group_capnp = capnp.load(_capnp_schema_file('group'))
user_capnp = capnp.load(_capnp_schema_file('user'))
user_public_key_capnp = capnp.load(_capnp_schema_file('user_public_key'))
domain_capnp = capnp.load(_capnp_schema_file('domain'))
repository_capnp = capnp.load(_capnp_schema_file('repository'))
changeset_capnp = capnp.load(_capnp_schema_file('changeset'))
change_capnp = capnp.load(_capnp_schema_file('change'))


class Object(object):
    """Base class for all objects used in Procession."""

    _KEY_FIELD = 'id'
    """String name of the field that serves as the key for the object."""

    _SINGULAR_NAME = None
    """The singular name of the object, lowercased. e.g. organization."""

    _PLURAL_NAME = None
    """The pluralized name of the object, lowercased. e.g. organizations."""

    _FIELD_NAME_TRANSLATIONS = {}
    """
    Dictionary of from: to members containing field name translations. from
    should be the Cap'n'p field naming convention (camelCased), with to being
    the Python and overall Procession naming convention (under_score).
    """

    _REVERSE_FIELD_NAME_TRANSLATIONS = None
    """
    Cache for reverse lookup of the field names. The _get_capnp_field_name()
    method handles populating this cache.
    """

    _FIELD_VALUE_TRANSLATORS = {
    }
    """
    Dict of names of any fields that should automatically have
    incoming values translated into some other type. The keys for
    the dict should be the `lower_with_underscore` field names. The
    values should be a translator functor from `procession.translators`
    """

    _CAPNP_OBJECT = None
    """
    The loaded capnp module for this object.
    e.g. organization_capnp.Organization.
    """

    def __init__(self, capnp_message, ctx=None, is_new=True):
        """
        Constructs a new object from a capnp message object and an optional
        `procession.context.Context` object. If the context object is None,
        then calling save(), update(), or remove() without supplying a context
        object will result in a `procession.exc.NoContext` exception being
        thrown.

        :param capnp_message: Cap'N'Proto message describing the object data.
        :param ctx: Optional `procession.context.Context` object.
        :param is_new: Optional boolean indicating whether the object is a new
                       object and has never been saved to backend storage.
        """
        self.__dict__['_ctx'] = ctx
        self.__dict__['_message'] = capnp_message
        self.__dict__['_is_new'] = is_new
        schema_fields = capnp_message.schema.fieldnames if is_new else []
        self.__dict__['_changed_fields'] = set(schema_fields)

    @property
    def ctx(self):
        return self.__dict__['_ctx']

    @property
    def is_new(self):
        """
        Returns True if the object has never been saved to backing storage,
        False otherwise.
        """
        return self.__dict__['_is_new']

    @property
    def key(self):
        tx_key = self._get_capnp_field_name(self._KEY_FIELD)
        return getattr(self.__dict__['_message'], tx_key)

    @property
    def has_changed(self):
        """Returns True if the object has any unsaved changes."""
        return len(self.__dict__['_changed_fields']) > 0

    @property
    def changed_field_values(self):
        """
        Returns a dict of all field values that have changed since last save.
        """
        raw = {k: v for k, v in self.__dict__['_message'].to_dict().items()
               if k in self.__dict__['_changed_fields']}
        return self.field_names_to_capnp(raw)

    def __setattr__(self, key, value):
        tx_key = self._get_capnp_field_name(key)
        if key in self._FIELD_VALUE_TRANSLATORS:
            translator = self._FIELD_VALUE_TRANSLATORS[key]
            value = translator(value)
        # Mark this field as changed in our set() of changed keys
        self.__dict__['_changed_fields'].add(key)
        return setattr(self._message, tx_key, value)

    def __getattr__(self, key):
        tx_key = self._get_capnp_field_name(key)
        value = getattr(self.__dict__['_message'], tx_key)
        if key in self._FIELD_VALUE_TRANSLATORS:
            translator = self._FIELD_VALUE_TRANSLATORS[key]
            reverser = getattr(translator, 'reverser')
            if callable(reverser):
                value = reverser(value)
        return value

    @staticmethod
    def _find_ctx(ctx_or_req):
        if isinstance(ctx_or_req, context.Context):
            return ctx_or_req
        else:
            return rest_context.from_http_req(ctx_or_req)

    def _ctx_or_raise(self, ctx=None):
        ctx = ctx or self.ctx
        if ctx is None:
            raise exc.NoContext()
        return ctx

    @classmethod
    def field_names_to_capnp(cls, values):
        """
        Returns values with the key names translated to the expected
        Cap'n'p field naming convention (camelCased).

        :param values: Dict containing the fields and values.
        """
        result = {}
        for k, v in values.items():
            tx_key = cls._get_capnp_field_name(k)
            result[tx_key] = v
        return result

    @classmethod
    def _get_capnp_field_name(cls, name):
        """
        Returns the Cap'n'p field name corresponding to the supplied "normal"
        Python field name. Uses a class-level reverse lookup cache.
        """
        if cls._REVERSE_FIELD_NAME_TRANSLATIONS is None:
            rev_map = {v: k for k, v in cls._FIELD_NAME_TRANSLATIONS.items()}
            cls._REVERSE_FIELD_NAME_TRANSLATIONS = rev_map
        return cls._REVERSE_FIELD_NAME_TRANSLATIONS.get(name, name)

    @classmethod
    def from_capnp(cls, fp, ctx=None):
        """
        Read a Cap'n'p binary stream (non-packed) and construct a new Cap'n'p
        message from the payload, returning an object of the approriate type.
        Automatically handles version translation with Cap'n'p's built-in
        protocol evolution.

        :param fp: File object to read.
        :param ctx: Optional `procession.context.Context` object.
        :returns An object of the appropriate subclass.
        """
        return cls(cls._CAPNP_OBJECT.read(fp), ctx=ctx)

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
        values = cls.field_names_to_capnp(deser_body)
        return cls(cls._CAPNP_OBJECT.new_message(**values), ctx=ctx)

    @classmethod
    def from_values(cls, ctx=None, is_new=True, **values):
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
        return cls.from_dict(values, ctx=ctx)

    @classmethod
    def from_dict(cls, subject, ctx=None, is_new=True):
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
        subject_copy = cls.field_names_to_capnp(subject_copy)
        return cls(cls._CAPNP_OBJECT.new_message(**subject_copy),
                   ctx=ctx,
                   is_new=is_new)

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
        return cls.from_dict(data, ctx=ctx, is_new=False)

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
            return cls.from_dict(data, ctx=ctx, is_new=False)

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
        return cls.from_dict(data, ctx=search_spec.ctx, is_new=False)

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
            res.append(cls.from_dict(record,
                                     ctx=search_spec.ctx,
                                     is_new=False))
        return res

    def to_dict(self):
        """
        Returns a Python dict of the fields in the object.

        :note The key names will be the translated under_score_names, not the
              Cap'n'p field names (camelCased).
        :note The values will be converted from the Cap'n'p message field
              format to the appropriate expected native Python type for the
              field. For example, `datetime.datetime` objects will be returned
              for timestamp fields, which are actually stored as strings in the
              Cap'n'p message struct.
        """
        raw = self.__dict__['_message'].to_dict()
        for capnp_key, tx_key in self._FIELD_NAME_TRANSLATIONS.items():
            if capnp_key in raw:
                raw[tx_key] = raw.pop(capnp_key)
        for field, translator in self._FIELD_VALUE_TRANSLATORS.items():
            reverser = getattr(translator, 'reverser')
            if field in raw and callable(reverser):
                raw[field] = reverser(raw[field])
        return raw

    def add_relation(self, child_obj_type, child_key):
        """
        Used to add a child key to a many to many relationship.

        :param child_obj_type: `procession.objects.Object` class of
                               child object.
        :param child_key: Key for the child object to relate to this object.
        :raises `procession.exc.NotFound` if no such object found in backend
                storage.
        """
        parent_obj_type = self.__class__
        self.ctx.store.add_relation(parent_obj_type,
                                    self.key,
                                    child_obj_type,
                                    child_key)

    def remove_relation(self, child_obj_type, child_key):
        """
        Used to remove a child key from a many to many relationship.

        :param child_obj_type: `procession.objects.Object` class of
                               child object.
        :param child_key: Key for the child object to disassociate to this object.
        :raises `procession.exc.NotFound` if no such object found in backend
                storage.
        """
        parent_obj_type = self.__class__
        self.ctx.store.remove_relation(parent_obj_type,
                                       self.key,
                                       child_obj_type,
                                       child_key)

    def delete(self, ctx=None):
        """
        Removes the object from backend storage. If the context object is None,
        then calling this method without the object already having a context
        object will result in a `procession.exc.NoContext` exception being
        thrown.

        :param ctx: Optional `procession.context.Context` object.
        """
        ctx = self._ctx_or_raise(ctx)
        # TODO(jaypipes): Implement ACLs here.
        ctx.store.delete(self.__class__, self.key)

    def save(self, ctx=None):
        """
        Saves the object to backend storage. If the context object is None,
        then calling this method without the object already having a context
        object will result in a `procession.exc.NoContext` exception being
        thrown.

        After a successful save() operation, the object's fields may be
        different -- for example, autoincrementing sequences or auto-generated
        timestamp fields may have been generated.

        :param ctx: Optional `procession.context.Context` object.
        """
        ctx = self._ctx_or_raise(ctx)
        # TODO(jaypipes): Implement ACLs here.
        self = ctx.store.save(self)  # Yes, we overwrite the object itself.


class Organization(Object):
    _SINGULAR_NAME = 'organization'
    _PLURAL_NAME = 'organizations'
    _FIELD_NAME_TRANSLATIONS = {
        'createdOn': 'created_on',
        'leftSequence': 'left_sequence',
        'parentOrganizationId': 'parent_organization_id',
        'rightSequence': 'right_sequence',
        'rootOrganizationId': 'root_organization_id',
    }
    _FIELD_VALUE_TRANSLATORS = {
        'created_on': translators.coerce_iso8601_string,
        'parent_organization_id': translators.coerce_none_to_nullstring,
    }
    _CAPNP_OBJECT = organization_capnp.Organization


class Group(Object):
    _SINGULAR_NAME = 'group'
    _PLURAL_NAME = 'groups'
    _FIELD_NAME_TRANSLATIONS = {
        'createdOn': 'created_on',
        'rootOrganizationId': 'root_organization_id',
    }
    _FIELD_VALUE_TRANSLATORS = {
        'created_on': translators.coerce_iso8601_string,
    }
    _CAPNP_OBJECT = group_capnp.Group

    def get_users(self, search_spec=None):
        store = self.ctx.store
        if search_spec is None:
            search_spec = search.SearchSpec(self.ctx)
        search_spec.filter_by(group_id=self.id)
        return store.get_relations(Group, User, search_spec)

    def add_user(self, user_id):
        self.add_relation(User, user_id)

    def remove_user(self, user_id):
        self.remove_relation(User, user_id)


class User(Object):
    _SINGULAR_NAME = 'user'
    _PLURAL_NAME = 'users'
    _FIELD_NAME_TRANSLATIONS = {
        'createdOn': 'created_on',
    }
    _FIELD_VALUE_TRANSLATORS = {
        'created_on': translators.coerce_iso8601_string,
    }
    _CAPNP_OBJECT = user_capnp.User

    def get_public_keys(self, search_spec=None):
        if search_spec is None:
            search_spec = search.SearchSpec(ctx=self.ctx)
            search_spec.filter_by(userId=self.id)
        return UserPublicKey.get_many(search_spec)

    def get_groups(self, search_spec=None):
        store = self.ctx.store
        if search_spec is None:
            search_spec = search.SearchSpec(self.ctx)
        search_spec.filter_by(user_id=self.id)
        return store.get_relations(User, Group, search_spec)

    def add_to_group(self, group_id):
        self.add_relation(Group, group_id)

    def remove_from_group(self, group_id):
        self.remove_relation(Group, group_id)


class UserPublicKey(Object):
    _SINGULAR_NAME = 'user_public_key'
    _PLURAL_NAME = 'user_public_keys'
    _FIELD_NAME_TRANSLATIONS = {
        'createdOn': 'created_on',
        'publicKey': 'public_key',
        'userId': 'user_id',
    }
    _FIELD_VALUE_TRANSLATORS = {
        'created_on': translators.coerce_iso8601_string,
    }
    _CAPNP_OBJECT = user_public_key_capnp.UserPublicKey


class Domain(Object):
    _SINGULAR_NAME = 'domain'
    _PLURAL_NAME = 'domains'
    _FIELD_NAME_TRANSLATIONS = [
        ('createdOn', 'created_on'),
        ('ownerId', 'owner_id'),
    ]
    _FIELD_VALUE_TRANSLATORS = {
        'created_on': translators.coerce_iso8601_string,
    }
    _CAPNP_OBJECT = domain_capnp.Domain

    def get_repos(self, search_spec=None):
        store = self.ctx.store
        if search_spec is None:
            search_spec = search.SearchSpec(ctx=self.ctx)
            search_spec.filter_by(domainId=self.id)
        return store.get_relations(Domain, Repository, search_spec)


class Repository(Object):
    _SINGULAR_NAME = 'repository'
    _PLURAL_NAME = 'repositories'
    _FIELD_NAME_TRANSLATIONS = {
        'createdOn': 'created_on',
        'domainId': 'domain_id',
        'ownerId': 'owner_id',
    }
    _FIELD_VALUE_TRANSLATORS = {
        'created_on': translators.coerce_iso8601_string,
    }
    _CAPNP_OBJECT = repository_capnp.Repository


class Changeset(Object):
    _SINGULAR_NAME = 'changeset'
    _PLURAL_NAME = 'changesets'
    _FIELD_NAME_TRANSLATIONS = {
        'commitMessage': 'commit_message',
        'createdOn': 'created_on',
        'targetBranch': 'target_branch',
        'targetRepoId': 'target_repo_id',
        'uploadedBy': 'uploaded_by',
    }
    _FIELD_VALUE_TRANSLATORS = {
        'created_on': translators.coerce_iso8601_string,
    }
    _CAPNP_OBJECT = changeset_capnp.Changeset


class Change(Object):
    _SINGULAR_NAME = 'change'
    _PLURAL_NAME = 'changes'
    _FIELD_NAME_TRANSLATIONS = {
        'createdOn': 'created_on',
        'changesetId': 'changeset_id',
        'uploadedBy': 'uploaded_by',
    }
    _FIELD_VALUE_TRANSLATORS = {
        'created_on': translators.coerce_iso8601_string,
    }
    _CAPNP_OBJECT = change_capnp.Change
