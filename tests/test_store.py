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

import fixtures
import mock
import testtools

from procession import config
from procession import store
from procession.storage import base as base_storage

from tests import base


class FakeDriver(base_storage.Driver):
    def __init__(self, conf):
        self.conf = conf
        self.deleted = False
        self.saved = False
        self.relations = set()

    def get_one(self, obj_type, search_spec):
        return mock.sentinel.get_one

    def get_many(self, obj_type, search_spec):
        return mock.sentinel.get_many

    def exists(self, obj_type, key):
        return mock.sentinel.exists

    def delete(self, obj_type, keys):
        self.deleted = True

    def save(self, obj):
        self.saved = True

    def add_relation(self, parent_obj_type, child_obj_type,
                     parent_key, child_key):
        self.relations.add((parent_obj_type,
                            child_obj_type,
                            parent_key,
                            child_key))

    def remove_relation(self, parent_obj_type, child_obj_type,
                        parent_key, child_key):
        self.relations.remove((parent_obj_type,
                               child_obj_type,
                               parent_key,
                               child_key))

    def get_relations(self, parent_obj_type, child_obj_type,
                      parent_search_spec, child_search_spec=None):
        return mock.sentinel.get_relations


class AddFakeStoreDriver(fixtures.Fixture):
    def _setUp(self):
        self.orig_drivers = store._VALID_STORE_DRIVERS
        self.orig_driver_cls_map = store._STORE_DRIVER_CLS_MAP
        store._VALID_STORE_DRIVERS = ('fake', )
        store._STORE_DRIVER_CLS_MAP = {'fake': FakeDriver}

        self.addCleanup(setattr, store, '_VALID_STORE_DRIVERS',
                        self.orig_drivers)
        self.addCleanup(setattr, store, '_STORE_DRIVER_CLS_MAP',
                        self.orig_driver_cls_map)


class TestBadStore(base.UnitTest):
    def test_bad_store_driver(self):
        store_conf = {
            'driver': 'unknown'
        }
        conf = config.Config(store=store_conf)
        with testtools.ExpectedException(RuntimeError):
            store.Store(conf)


class TestStoreInterface(base.UnitTest):
    def setUp(self):
        super(TestStoreInterface, self).setUp()
        self.useFixture(AddFakeStoreDriver())
        store_conf = {
            'driver': 'fake'
        }
        conf = config.Config(store=store_conf)
        self.store_obj = store.Store(conf)

    def test__init__(self):
        self.assertEqual('fake', self.store_obj.driver.conf.store.driver)

    def test_get_one(self):
        r = self.store_obj.get_one(mock.sentinel.obj_type, mock.sentinel.key)
        self.assertEqual(mock.sentinel.get_one, r)

    def test_get_many(self):
        r = self.store_obj.get_many(mock.sentinel.obj_type, mock.sentinel.key)
        self.assertEqual(mock.sentinel.get_many, r)

    def test_exists(self):
        r = self.store_obj.exists(mock.sentinel.obj_type, mock.sentinel.key)
        self.assertEqual(mock.sentinel.exists, r)

    def test_delete(self):
        self.assertFalse(self.store_obj.driver.deleted)
        self.store_obj.delete(mock.sentinel.obj_type, mock.sentinel.key)
        self.assertTrue(self.store_obj.driver.deleted)

    def test_save(self):
        self.assertFalse(self.store_obj.driver.saved)
        self.store_obj.save(mock.sentinel.obj)
        self.assertTrue(self.store_obj.driver.saved)

    def test_get_relations(self):
        r = self.store_obj.get_relations(mock.sentinel.parent_obj_type,
                                         mock.sentinel.child_obj_type,
                                         mock.sentinel.parent_search)
        self.assertEqual(mock.sentinel.get_relations, r)

    def test_modify_relations(self):
        rel_key = (mock.sentinel.parent_obj_type,
                   mock.sentinel.child_obj_type,
                   mock.sentinel.parent_key,
                   mock.sentinel.child_key)
        self.assertEqual(set(), self.store_obj.driver.relations)
        self.store_obj.add_relation(mock.sentinel.parent_obj_type,
                                    mock.sentinel.child_obj_type,
                                    mock.sentinel.parent_key,
                                    mock.sentinel.child_key)
        self.assertEqual(set([rel_key]), self.store_obj.driver.relations)
        self.store_obj.remove_relation(mock.sentinel.parent_obj_type,
                                       mock.sentinel.child_obj_type,
                                       mock.sentinel.parent_key,
                                       mock.sentinel.child_key)
        self.assertEqual(set(), self.store_obj.driver.relations)
