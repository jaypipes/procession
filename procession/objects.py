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

import jsonschema

UUID_REGEX_STRING = (r'^([0-9a-fA-F]){8}-*([0-9a-fA-F]){4}-*([0-9a-fA-F]){4}'
                     r'-*([0-9a-fA-F]){4}-*([0-9a-fA-F]){12}$')


class ObjectBase(object):

    """
    Base class that all objects in the object model derive from.
    """

    VERSION = None
    """The tuple (MAJOR, INCREMENT) current version of the object model"""

    SCHEMA = None
    """The JSON-Schema object that describes the object's attributes"""

    @classmethod
    def from_py_object(cls, py_object):
        """
        Given a supplied dict or list (typically coming in directly from an
        API request body that has been deserialized), construct an object
        and validate that properties of the list or dict match the schema
        of the object.

        :raises `jsonschema.ValidationError` if the object model's schema
                does not match the supplied instance structure.
        """
        jsonschema.validate(py_object, cls.SCHEMA)
        orig = copy.deepcopy(py_object)
        # Set nullable attributes to None if not in incoming
        # object's keys (if incoming object is a dict)
        if isinstance(py_object, dict):
            fields = cls.SCHEMA["properties"].keys()
            for field in fields:
                if field not in py_object:
                    orig[field] = None

        res = cls()
        object.__setattr__(res, '_data', orig)
        object.__setattr__(res, '_original', orig)
        return res

    @classmethod
    def from_db(cls, db_model):
        """
        Construct an object of this type from a DB model object.
        Does no validation of the incoming database model.

        :param db_model: The SQLAlchemy model for this object.
        """
        fields = cls.SCHEMA["properties"].keys()
        # We bypass ObjectBase.setattr(), since it does validation
        values = {}
        for field in fields:
            values[field] = getattr(db_model, field)
        res = cls()
        object.__setattr__(res, '_data', values)
        object.__setattr__(res, '_original', values)
        return res

    def __getattr__(self, key):
        """
        Simple translation of a object.attr getter to the underlying
        dict storage.

        :raises `AttributeError` if key not in object's data dict
        """
        # Avoid infinite recursion by accessing the special __dict__
        # mapping of fields, which bypasses the getattr lookup.
        if key in self.__dict__['_data']:
            return self.__dict__['_data'][key]
        raise AttributeError(key)

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


class Organization(ObjectBase):

    SCHEMA = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "title": "A hierarchical container of zero or more other "
                 "organizations.",
        "additionalProperties": False,
        "properties": {
            "id": {
                "type": "integer",
                "description": "Identifier for the organization.",
            },
            "display_name": {
                "type": "string",
                "description": "Name displayed for the organization.",
                "maxLength": 50
            },
            "name": {
                "type": "string",
                "description": "Short name for the organization (used in "
                               "determining the organization's 'slug' value)",
                "maxLength": 30
            },
            "slug": {
                "type": "string",
                "description": "Lowercased, hyphenated non-UUID identififer "
                               "used in URIs.",
                "maxLength": 100
            },
            "created_on": {
                "type": "string",
                "description": "The date-time when the organization was "
                               "created, in ISO 8601 format.",
                "format": "date-time"
            },
            "root_organization_id": {
                "type": "integer",
                "description": "The ID of the root organization of the "
                               "organization tree that this organization "
                               "belongs to. Can be the same as the value "
                               "of this organization's id attribute.",
            },
            "parent_organization_id": {
                "type": "integer",
                "description": "The ID of the immediate parent "
                               "organization of this organization "
                               "or null if this organization is a root "
                               "organization."
            }
        }
    }


class Group(ObjectBase):

    SCHEMA = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "title": "A collection of users within an organization.",
        "additionalProperties": False,
        "properties": {
            "id": {
                "type": "integer",
                "description": "Identifier for the group."
            },
            "display_name": {
                "type": "string",
                "description": "Name displayed for the group.",
                "maxLength": 60
            },
            "name": {
                "type": "string",
                "description": "Short name for the group (used in "
                               "determining the group's 'slug' value). Must "
                               "be unique within the containing organization.",
                "maxLength": 30
            },
            "slug": {
                "type": "string",
                "description": "Lowercased, hyphenated non-UUID identififer "
                               "used in URIs.",
                "maxLength": 100
            },
            "root_organization_id": {
                "type": "integer",
                "description": "The ID of the root organization of the "
                               "organization tree that this group belongs to."
            },
            "created_on": {
                "type": "string",
                "description": "The date-time when the organization was "
                               "created, in ISO 8601 format.",
                "format": "date-time"
            }
        }
    }


class User(ObjectBase):

    SCHEMA = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "title": "A user within the Procession deployment.",
        "additionalProperties": False,
        "properties": {
            "id": {
                "type": "integer",
                "description": "Identifier for the user."
            },
            "display_name": {
                "type": "string",
                "description": "Name displayed for the user.",
                "maxLength": 50
            },
            "name": {
                "type": "string",
                "description": "Short name for the user (used in "
                               "determining the user's 'slug' value).",
                "maxLength": 30
            },
            "slug": {
                "type": "string",
                "description": "Lowercased, hyphenated non-UUID identififer "
                               "used in URIs.",
                "maxLength": 40
            },
            "email": {
                "type": "string",
                "description": "Email address to use for the user.",
                "maxLength": 80,
                "format": "email"
            },
            "created_on": {
                "type": "string",
                "description": "The date-time when the organization was "
                               "created, in ISO 8601 format.",
                "format": "date-time"
            }
        }
    }


class UserPublicKey(ObjectBase):

    SCHEMA = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "title": "An SSH key pair for a user.",
        "additionalProperties": False,
        "properties": {
            "user_id": {
                "type": "integer",
                "description": "Identifier for the user."
            },
            "fingerprint": {
                "type": "string",
                "description": "Fingerprint of the SSH key.",
                "minLength": 32,
                "maxLength": 40
            },
            "public_key": {
                "type": "string",
                "description": "Public key part of SSH key pair."
            },
            "created_on": {
                "type": "string",
                "description": "The date-time when the organization was "
                               "created, in ISO 8601 format.",
                "format": "date-time"
            }
        }
    }


class Domain(ObjectBase):

    SCHEMA = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "title": "A single-level container for SCM repositories under "
                 "Procession's control.",
        "additionalProperties": False,
        "properties": {
            "id": {
                "type": "integer",
                "description": "Identifier for the domain."
            },
            "name": {
                "type": "string",
                "description": "Name for the domain (used in "
                               "determining the user's 'slug' value).",
                "maxLength": 50
            },
            "slug": {
                "type": "string",
                "description": "Lowercased, hyphenated non-UUID identififer "
                               "used in URIs.",
                "maxLength": 60
            },
            "created_on": {
                "type": "string",
                "description": "The date-time when the organization was "
                               "created, in ISO 8601 format.",
                "format": "date-time"
            },
            "owner_id": {
                "type": "integer",
                "description": "Identifier for the user who owns the domain."
            },
            "visibility": {
                "type": "string",
                "choices": [
                    "ALL",
                    "RESTRICTED"
                ]
            }
        }
    }


class Repository(ObjectBase):

    SCHEMA = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "title": "An SCM repositories under Procession's control.",
        "additionalProperties": False,
        "properties": {
            "id": {
                "type": "integer",
                "description": "Identifier for the repository."
            },
            "domain_id": {
                "type": "integer",
                "description": "Identifier for the domain."
            },
            "name": {
                "type": "string",
                "description": "Name for the repository. Must be unique "
                               "within the domain.",
                "maxLength": 50
            },
            "created_on": {
                "type": "string",
                "description": "The date-time when the organization was "
                               "created, in ISO 8601 format.",
                "format": "date-time"
            },
            "owner_id": {
                "type": "integer",
                "description": "Identifier for the user who owns the "
                               "repository."
            }
        }
    }


class Changeset(ObjectBase):

    SCHEMA = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "title": "A series of proposed changes to a repository.",
        "additionalProperties": False,
        "properties": {
            "id": {
                "type": "integer",
                "description": "Identifier for the changeset."
            },
            "target_repo_id": {
                "type": "integer",
                "description": "Identifier for the target repository."
            },
            "target_branch": {
                "type": "string",
                "description": "Name of the SCM branch that the changeset "
                               "intends to merge into.",
                "maxLength": 200
            },
            "created_on": {
                "type": "string",
                "description": "The date-time when the organization was "
                               "created, in ISO 8601 format.",
                "format": "date-time"
            },
            "uploaded_by": {
                "type": "integer",
                "description": "Identifier of the user who originally "
                               "uploaded the changeset."
            },
            "commit_message": {
                "type": "string",
                "description": "The commit message that will be used when "
                               "the changeset is merged into the target "
                               "branch."
            },
            "state": {
                "type": "string",
                "description": "Indicator of the current state of the "
                               "changeset.",
                "choices": [
                    "ABANDONED",
                    "DRAFT",
                    "ACTIVE",
                    "CLEARED",
                    "MERGED"
                ]
            }
        }
    }


class Change(ObjectBase):

    SCHEMA = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "title": "A single change within a changeset.",
        "additionalProperties": False,
        "properties": {
            "changeset_id": {
                "type": "integer",
                "description": "Identifier for the changeset."
            },
            "sequence": {
                "type": "integer",
                "description": "Sequence number of the patch within the "
                               "changeset."
            },
            "created_on": {
                "type": "string",
                "description": "The date-time when the organization was "
                               "created, in ISO 8601 format.",
                "format": "date-time"
            },
            "uploaded_by": {
                "type": "integer",
                "description": "Identifier of the user who originally "
                               "uploaded the change."
            }
        }
    }
