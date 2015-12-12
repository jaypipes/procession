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

    def save(self, obj):
        """
        Writes the supplied object to backend storage. A new object of the same
        type is returned, possibly with some new fields set -- e.g.
        autoincrementing sequences or auto-generated timestamp fields.

        :param obj: A `procession.objects.Object` instance.
        :returns A new `procession.objects.Object` instance of the same type as
                 the supplied object.
        """
        obj_name = obj._SINGULAR_NAME
        sess = self._get_session()
        if obj.is_new:
            values = obj.to_dict()
            db_model = self._create_object(sess, obj_name, values)
        else:
            values = obj.changed_field_values
            db_model = self._update_object(sess, obj_name, obj.key, values)
        model_dict = db_model.to_dict()
        return obj.from_dict(model_dict, ctx=obj.ctx, is_new=False)

    def _create_object(self, sess, obj_name, values):
        func_map = {
            'user': api.user_create,
            'organization': api.organization_create,
            'group': api.group_create,
            'domain': api.domain_create,
            'repository': api.repo_create,
            'changeset': api.changeset_create,
        }
        api_fn = func_map[obj_name]
        return api_fn(sess, values)

    def _update_object(self, sess, obj_name, key, values):
        func_map = {
            'user': api.user_update,
            'group': api.group_update,
            'domain': api.domain_update,
            'repository': api.repo_update,
        }
        api_fn = func_map[obj_name]
        return api_fn(sess, key, values)
