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

import logging

import sqlalchemy
from sqlalchemy.orm import sessionmaker

from procession import exc
from procession.storage.sql import models
from procession.storage.sql import api

_LOG = logging.getLogger(__name__)
_OBJECT_TO_DB_MODEL_MAP = {
    'organization': models.Organization,
    'group': models.Group,
    'user': models.User,
    'domain': models.Domain,
    'user_public_key': models.UserPublicKey,
    'repository': models.Repository,
    'changeset': models.Changeset,
    'change': models.Change
}


def _get_db_model_from_obj_class(obj_class):
    obj_type = obj_class._SINGULAR_NAME
    try:
        return _OBJECT_TO_DB_MODEL_MAP[obj_type]
    except KeyError:
        raise exc.UnknownObjectType(obj_class)


class Driver(object):

    def __init__(self, conf):
        """
        Constructs the SQL driver.

        :param conf:
            A `procession.config.Config` object.
        :raises RuntimeError if unable to configure driver correctly.
        """
        self.conf = conf
        db_connection = conf.sql.connection
        self.engine = sqlalchemy.create_engine(db_connection)
        self.sessionmaker = sessionmaker(bind=self.engine)
        self.session = None

    def _get_session(self):
        """Returns the active session object."""
        if self.session is None:
            self.session = self.sessionmaker(autocommit=False)
        return self.session

    def init(self):
        """
        Do any startup/once-only actions.
        """
        # TODO(jaypipes): Use Alembic migrations only, not create_all()
        models.ModelBase.metadata.create_all(self.engine)

    def get_one(self, obj_type, search_spec):
        """
        Returns a single Python dict that matches the supplied search spec.

        :param obj_type: A `procession.objects.Object` class.
        :param search_spec: A `procession.search.SearchSpec`
        :raises `procession.exc.NotFound` if no such object found in backend
                storage.
        """
        sess = self._get_session()
        model = _get_db_model_from_obj_class(obj_type)

        filters = search_spec.filters
        db_model = api.get_one(sess, model, **filters)
        return db_model.to_dict()

    def get_relations(self, parent_obj_type, child_obj_type,
                      parent_search_spec, child_search_spec=None):
        """
        Returns a list of Python dicts of records of the child type
        that match the supplied search spec for the parent and
        child relation types. Used for many-to-many relationship traversal,
        for instance with user -> group membership.

        :param parent_obj_type: A `procession.objects.Object` class for the
                                parent side of the relation.
        :param child_obj_type: A `procession.objects.Object` class for the
                               child side of the relation.
        :param parent_search_spec: A `procession.search.SearchSpec` object with
                                   conditions for the parent side of the
                                   relation.
        :param child_search_spec: A `procession.search.SearchSpec` object with
                                  conditions for the child side of the
                                  relation.
        """
        func_map = {
            ('user', 'group'): api.user_groups_get
        }
        sess = self._get_session()
        parent_obj_name = parent_obj_type._SINGULAR_NAME
        child_obj_name = child_obj_type._SINGULAR_NAME
        map_key = (parent_obj_name, child_obj_name)
        try:
            api_fn = func_map[map_key]
        except KeyError:
            raise exc.InvalidRelation
        db_models = api_fn(sess, parent_search_spec, child_search_spec)
        return [db_model.to_dict() for db_model in db_models]

    def get_many(self, obj_type, search_spec):
        """
        Returns a list of Python dicts of records that match the supplied
        search spec.

        :param obj_type: A `procession.objects.Object` class.
        :param search_spec: A `procession.search.SearchSpec` object.
        """
        sess = self._get_session()
        model = _get_db_model_from_obj_class(obj_type)
        db_models = api.get_many(sess, model, search_spec)
        return [db_model.to_dict() for db_model in db_models]

    def exists(self, obj_type, key):
        """
        Returns True if an object of the supplied type and key exists
        in backend storage.

        :param obj_type: A `procession.objects.Object` class.
        :param key: string key for the object.
        """
        sess = self._get_session()
        model = _get_db_model_from_obj_class(obj_type)
        return api.exists(sess, model, key)

    def delete(self, obj_type, key):
        """
        Deletes all objects of the supplied type with matching supplied
        keys from backend storage.

        :param obj_type: A `procession.objects.Object` class.
        :param key: string key for the object.
        """
        func_map = {
            'user': api.user_delete,
            'organization': api.organization_delete,
            'group': api.group_delete,
            'domain': api.domain_delete,
            'repository': api.repo_delete,
            'changeset': api.changeset_delete,
        }
        obj_name = obj_type._SINGULAR_NAME
        sess = self._get_session()
        api_fn = func_map[obj_name]
        api_fn(sess, key)

    def save(self, obj_type, key, **values):
        """
        Writes the supplied field values for an object type to backend storage.

        :param obj_type: A `procession.objects.Object` class.
        :param key: A string key for the record.
        :param **values: Dictionary of field values to set on the object.
        :raises `procession.exc.Duplicate` if an object with the same
                identifier(s) already exists.
        """
        pass
