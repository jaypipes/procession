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

from procession import exc
from procession import helpers
from procession.db import models
from procession.db import session

LOG = logging.getLogger(__name__)
UUID_REGEX_STRING = (r'^([0-9a-fA-F]){8}-*([0-9a-fA-F]){4}-*([0-9a-fA-F]){4}'
                     r'-*([0-9a-fA-F]){4}-*([0-9a-fA-F]){12}$')


class ObjectBase(object):

    """
    Base class that all objects in the object model derive from.
    """

    SCHEMA = None
    """The JSON-Schema object that describes the object's attributes"""

    DB_MODEL = None
    """The database model used when persisting the object to storage"""

    @classmethod
    def from_json(cls, json_instance):
        """
        Given a supplied dict or list (typically coming in directly from an
        API request body that has been deserialized), construct an object
        and validate that properties of the list or dict match the schema
        of the object model.

        :raises `jsonschema.ValidationError` if the object model's schema
                does not match the supplied instance structure.
        """
        orig = copy.deepcopy(json_instance)
        result = cls()
        object.__setattr__(result, '_data', orig)
        object.__setattr__(result, '_original', orig)
        jsonschema.validate(json_instance, cls.SCHEMA)

    def __init__(self, **kwargs):
        #NOTE(jaypipes): We need to use object.__setattr__ here because
        # we override the setattr below
        object.__setattr__(self, '_new', kwargs.get('new', False))
        object.__setattr__(self, '_db_obj', None)

    def __getattr__(self, key):
        """
        Simple translation of a object.attr getter to the underlying
        dict storage.

        :raises `KeyError` if key not in object's data dict
        """
        if key in self._data:
            return self._data[key]
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

    def patch(self):
        """
        Returns a JSON-Patch document representing any changes that have
        been made to the object since the object was initially constructed
        with the JSON instance.
        """
        return jsonpatch.make_patch(self._original, self._data)

    def save(self, ctx, **kwargs):
        """
        Saves an object to database storage.

        :param ctx: `procession.context.Context` object
        :param kwargs: optional keywords arguments to the function:

            `session`: A session object to use

        :raises `procession.exc.Duplicate` if an object with same key already
                already exists in the database
        :raises `procession.exc.Invalid` if validation of object fails
        """
        sess = kwargs.get('session', session.get_session())

        o = self._db_obj
        if o is None:
            o = self.DB_MODEL()

        parent_org_id = None
        new_root = False
        if 'parent_organization_id' in attrs:
            # Validate that the supplied parent exists, and if so, set
            # the root organization ID to the parent's root organization.
            parent_org_id = attrs['parent_organization_id']
            try:
                parent = _get_one(sess, models.Organization, id=parent_org_id)
                root_org_id = parent.root_organization_id
            except exc.NotFound:
                msg = "The specified parent organization {0} does not exist."
                msg = msg.format(parent_org_id)
                raise exc.NotFound(msg)
            except sa_exc.StatementError:
                msg = "Parent organization ID {0} was badly formatted."
                msg = msg.format(parent_org_id)
                raise exc.BadInput(msg)
        else:
            # Parent and root organization were not specified, so we set
            # root org ID to this organization's ID
            o.id = root_org_id = uuid.uuid4()
            new_root = True
            o.left_sequence = 1
            o.right_sequence = 2

        # Before insertion, we validate that there is no top-level
        # organization (root organization) that shares the same org name.
        conn = sess.connection()
        org_table = models.Organization.__table__
        new_org_name = attrs['org_name']
        where_expr = expr.and_(org_table.c.org_name == new_org_name,
                               org_table.c.parent_organization_id == parent_org_id)
        sel = expr.select([org_table.c.id]).where(where_expr).limit(1)
        org_recs = conn.execute(sel).fetchall()
        if len(org_recs):
            msg = ("An organization at the same level with name {0} "
                   "already exists.")
            msg = msg.format(new_org_name)
            raise exc.Duplicate(msg)

        o.root_organization_id = root_org_id
        o.parent_organization_id = parent_org_id
        o.set_slug(session=sess)
        sess.add(o)

        if not new_root:
            _insert_organization_into_tree(ctx, o, session=sess)

        sess.commit()
        LOG.info("Added new organization {0} ({1}) with left of {2}.".format(
            o.id, o.org_name, o.left_sequence))
        return o


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
                "description": "The date-time when the organization was "
                               "created, in ISO 8601 format.",
                "format": "date-time"
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

    DB_MODEL = models.Organization


class Group(ObjectBase):

    SCHEMA = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "title": "A collection of users within an organization.",
        "additionalProperties": False,
        "properties": {
            "id": {
                "type": "string",
                "description": "UUID identifiers for the group.",
                "pattern": UUID_REGEX_STRING
            },
            "display_name": {
                "type": "string",
                "description": "Name displayed for the group.",
                "maxLength": 60,
            },
            "group_name": {
                "type": "string",
                "description": "Short name for the group (used in "
                               "determining the group's 'slug' value). Must "
                               "be unique within the containing organization.",
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
                "type": "string",
                "description": "UUID identifiers for the user.",
                "pattern": UUID_REGEX_STRING
            },
            "display_name": {
                "type": "string",
                "description": "Name displayed for the user.",
                "maxLength": 50,
            },
            "user_name": {
                "type": "string",
                "description": "Short name for the user (used in "
                               "determining the user's 'slug' value).",
                "maxLength": 30,
            },
            "slug": {
                "type": "string",
                "description": "Lowercased, hyphenated non-UUID identififer "
                               "used in URIs.",
                "maxLength": 40,
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
                "type": "string",
                "description": "UUID identifiers for the user.",
                "pattern": UUID_REGEX_STRING
            },
            "fingerprint": {
                "type": "string",
                "description": "Fingerprint of the SSH key.",
                "minLength": 32,
                "maxLength": 40,
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
                "type": "string",
                "description": "UUID identifiers for the domain.",
                "pattern": UUID_REGEX_STRING
            },
            "name": {
                "type": "string",
                "description": "Name for the domain (used in "
                               "determining the user's 'slug' value).",
                "maxLength": 50,
            },
            "slug": {
                "type": "string",
                "description": "Lowercased, hyphenated non-UUID identififer "
                               "used in URIs.",
                "maxLength": 60,
            },
            "created_on": {
                "type": "string",
                "description": "The date-time when the organization was "
                               "created, in ISO 8601 format.",
                "format": "date-time"
            },
            "owner_id": {
                "type": "string",
                "description": "UUID identifiers of the user who owns the domain.",
                "pattern": UUID_REGEX_STRING
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
                "type": "string",
                "description": "UUID identifiers for the repository.",
                "pattern": UUID_REGEX_STRING
            },
            "domain_id": {
                "type": "string",
                "description": "UUID identifiers of the domain this repository is under.",
                "pattern": UUID_REGEX_STRING
            },
            "name": {
                "type": "string",
                "description": "Name for the repository. Must be unique within "
                               "the domain.",
                "maxLength": 50,
            },
            "created_on": {
                "type": "string",
                "description": "The date-time when the organization was "
                               "created, in ISO 8601 format.",
                "format": "date-time"
            },
            "owner_id": {
                "type": "string",
                "description": "UUID identifiers of the user who owns the repository.",
                "pattern": UUID_REGEX_STRING
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
                "type": "string",
                "description": "UUID identifiers for the changeset.",
                "pattern": UUID_REGEX_STRING
            },
            "target_repo_id": {
                "type": "string",
                "description": "UUID identifiers of the repository the changeset is targeted at.",
                "pattern": UUID_REGEX_STRING
            },
            "target_branch": {
                "type": "string",
                "description": "Name of the SCM branch that the changeset intends to merge into.",
                "maxLength": 200,
            },
            "created_on": {
                "type": "string",
                "description": "The date-time when the organization was "
                               "created, in ISO 8601 format.",
                "format": "date-time"
            },
            "uploaded_by": {
                "type": "string",
                "description": "UUID identifiers of the user who originally uploaded the changeset.",
                "pattern": UUID_REGEX_STRING
            },
            "commit_message": {
                "type": "string",
                "description": "The commit message that will be used when the changeset is merged "
                               "into the target branch."
            },
            "state": {
                "type": "string",
                "description": "Indicator of the current state of the changeset.",
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
                "type": "string",
                "description": "UUID identifiers for the changeset the change belongs to.",
                "pattern": UUID_REGEX_STRING
            },
            "sequence": {
                "type": "integer",
                "description": "Sequence number of the patch within the changeset."
            },
            "created_on": {
                "type": "string",
                "description": "The date-time when the organization was "
                               "created, in ISO 8601 format.",
                "format": "date-time"
            },
            "uploaded_by": {
                "type": "string",
                "description": "UUID identifiers of the user who originally uploaded the changeset.",
                "pattern": UUID_REGEX_STRING
            }
        }
    }
