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

import jsonschema
import testtools

from procession import objects

from tests import base

TEST_SCHEMA = {
    "title": "Test Schema",
    "type": "object",
    "properties": {
        "first_name": {
            "type": "string"
        },
        "last_name": {
            "type": "string"
        },
        "age": {
            "description": "Age in years",
            "type": "integer",
            "minimum": 0
        }
    },
    "required": [
        "first_name",
        "last_name"
    ]
}


class TestObjects(base.UnitTest):

    def test_object_base(self):

        class MyObject(objects.ObjectBase):
            SCHEMA = TEST_SCHEMA

        instance = {
            'first_name': 'Albert',
            'last_name': 'Einstein',
            'age': -1  # Must be greater than or equal to zero
        }
        with testtools.ExpectedException(jsonschema.ValidationError):
            MyObject.from_py_object(instance)

        instance = {
            'first_name': 'Albert',
            'last_name': 'Einstein',
            'age': 73
        }
        obj = MyObject.from_py_object(instance)
        with testtools.ExpectedException(jsonschema.ValidationError):
            obj.age = -1
        # Test that the above setter was replaced by the original
        # value...
        self.assertEquals(73, obj.age)

        # Test __getattr__ translation of KeyError to AttributeError
        with testtools.ExpectedException(AttributeError):
            obj.nonexistattr

        # Try creating an instance of the object without one of the
        # optional fields.
        instance = {
            'first_name': 'Albert',
            'last_name': 'Einstein'
        }
        obj = MyObject.from_py_object(instance)
        self.assertIsNone(obj.age)
