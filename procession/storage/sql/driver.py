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
_OBJECT_RELATIONS_MAP = {
    ('user', 'group'): api.user_groups_get
}


def _get_db_model_from_obj_class(obj_class):
    obj_type = obj_class._SINGULAR_NAME
    return _OBJECT_TO_DB_MODEL_MAP[obj_type]


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

    def _get_session(self):
        return self.sessionmaker(autocommit=False)

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
        sess = self._get_session()
        try:
            parent_obj_name = parent_obj_type._SINGULAR_NAME
            child_obj_name = child_obj_type._SINGULAR_NAME
            api_fn = _OBJECT_RELATIONS_MAP[(parent_obj_name, child_obj_name)]
        except KeyError:
            raise exc.InvalidRelation
        db_models = api_fn(sess, parent_search_spec)
        res = []
        for db_model in db_models:
            res.append(db_model.to_dict())
        return res

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
        res = []
        for db_model in db_models:
            res.append(db_model.to_dict())
        return res

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

    def remove(self, obj_type, keys):
        """
        Deletes all objects of the supplied type with matching supplied
        keys from backend storage.

        :param obj_type: A `procession.objects.Object` class.
        :param key: list of strings or string key for the object.
        """
        sess = self._get_session()
        model = _get_db_model_from_obj_class(obj_type)
        return api.remove(sess, model, keys)

    def save(self, obj):
        """
        Writes the supplied object to backend storage.

        :param obj: A `procession.objects.Object` object.
        :raises `procession.exc.Duplicate` if an object with the same
                identifier(s) already exists.
        """
        pass
