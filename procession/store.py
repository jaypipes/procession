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

import procession.storage.sql.driver

_VALID_STORE_DRIVERS = ('sql',)
_STORE_DRIVER_CLS_MAP = {
    'sql': procession.storage.sql.driver.Driver
}


class Store(object):
    """
    Interface for persisting and retrieving raw data from some backend
    storage system.
    """
    def __init__(self, conf):
        """
        Constructs the store.

        :param conf: A `procession.config.Config` object.
        :raises RuntimeError if unable to configure driver correctly.
        """
        store_driver = conf.store.driver.lower()
        if store_driver not in _VALID_STORE_DRIVERS:
            raise RuntimeError("Bad store driver: %s" % store_driver)

        self.driver = _STORE_DRIVER_CLS_MAP[store_driver](conf)

    def init(self):
        """
        Do any startup/once-only actions.
        """
        self.driver.init()

    def get_one(self, obj_type, search_spec):
        """
        Returns a single Python dict that matches the supplied search spec.

        :param obj_type: A `procession.objects.Object` class.
        :param search_spec: A `procession.search.SearchSpec` object.
        :raises `procession.exc.NotFound` if no such object found in backend
                storage.
        """
        return self.driver.get_one(obj_type, search_spec)

    def add_relation(self, parent_obj_type, child_obj_type,
                     parent_key, child_key):
        """
        Adds a many-to-many relation between a parent and a child object.

        :param parent_obj_type: A `procession.objects.Object` class for the
                                parent side of the relation.
        :param child_obj_type: A `procession.objects.Object` class for the
                               child side of the relation.
        :param parent_key: A string key for the parent record.
        :param child_key: A string key for the child record.
        :raises `procession.exc.NotFound` if either parent or child key
                does not exist in backend storage.
        """
        self.driver.add_relation(parent_obj_type, child_obj_type,
                                 parent_key, child_key)

    def remove_relation(self, parent_obj_type, child_obj_type,
                        parent_key, child_key):
        """
        Removes a many-to-many relation between a parent and a child object.

        :param parent_obj_type: A `procession.objects.Object` class for the
                                parent side of the relation.
        :param child_obj_type: A `procession.objects.Object` class for the
                               child side of the relation.
        :param parent_key: A string key for the parent record.
        :param child_key: A string key for the child record.
        :raises `procession.exc.NotFound` if either parent or child key
                does not exist in backend storage.
        """
        self.driver.remove_relation(parent_obj_type, child_obj_type,
                                    parent_key, child_key)

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
        return self.driver.get_relations(parent_obj_type,
                                         child_obj_type,
                                         parent_search_spec,
                                         child_search_spec)

    def get_many(self, obj_type, search_spec):
        """
        Returns a list of Python dicts of records that match the supplied
        search spec.

        :param obj_type: A `procession.objects.Object` class.
        :param search_spec: A `procession.search.SearchSpec` object.
        """
        return self.driver.get_many(obj_type, search_spec)

    def exists(self, obj_type, key):
        """
        Returns True if an object of the supplied type and key exists
        in backend storage.

        :param obj_type: A `procession.objects.Object` class.
        :param key: list of strings or string key for the object.
        """
        return self.driver.exists(obj_type)

    def remove(self, obj_type, keys):
        """
        Deletes all objects of the supplied type with matching supplied
        keys from backend storage.

        :param obj_type: A `procession.objects.Object` class.
        :param key: list of strings or string key for the object.
        """
        return self.driver.remove(obj_type, keys)

    def save(self, obj_type, **values):
        """
        Writes the supplied field values for an object type to backend storage.

        :param obj_type: A `procession.objects.Object` class.
        :raises `procession.exc.Duplicate` if an object with the same
                identifier(s) already exists.
        """
        self.driver.save(obj_type, **values)