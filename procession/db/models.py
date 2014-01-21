# -*- encoding: utf-8 -*-
#
# Copyright 2013 Jay Pipes
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

import datetime
import inspect
import logging
import re
import urlparse
import uuid

from oslo.config import cfg
import slugify
from sqlalchemy import orm
from sqlalchemy import schema
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext import declarative

from procession.db import session

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


# The following comes straight out of the SQLAlchemy documentation
# for a cross-database compatible GUID/UUID type:
# http://docs.sqlalchemy.org/en/rel_0_8/core/types.html
# #backend-agnostic-guid-type
class GUID(types.TypeDecorator):
    """
    Platform-independent GUID type.

    Uses Postgresql's UUID type, otherwise uses
    CHAR(32), storing as stringified hex values.
    """
    impl = types.CHAR

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(postgresql.UUID())
        else:
            return dialect.type_descriptor(types.CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return "%.32x" % uuid.UUID(value)
            else:
                # hexstring
                return "%.32x" % value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            return uuid.UUID(value)


# Straight from SQLAlchemy documentation for a Unicode auto-converted
# string type:
# http://docs.sqlalchemy.org/en/rel_0_8/core/types.html#coerce-to-unicode
class CoerceUTF8(types.TypeDecorator):
    """
    Safely coerce Python bytestrings to Unicode
    before passing off to the database.
    """

    impl = types.Unicode

    def process_bind_param(self, value, dialect):
        if isinstance(value, str):
            value = value.decode('utf-8')
        return value


class Fingerprint(types.TypeDecorator):
    """
    Simple CHAR-based type that removes colons from key fingerprints
    when inserting/updating values, and appends colons when displaying.
    """
    impl = types.CHAR
    fp_re = re.compile("[a-f0-9]{32,40}")

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(types.CHAR(40))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        else:
            # hexstring of either 128 or 160-bit fingerprint
            value = value.replace(':', '')
            if not self.fp_re.match(value):
                msg = ("Fingerprint must be a 128-bit or 160-bit valid "
                       "hexidecimal fingerprint.")
                raise ValueError(msg)
            return value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            # go from '435143a1b5fc8bb70a3aa9b10f6673a8'
            # to '43:51:43:a1:b5:fc:8b:b7:0a:3a:a9:b1:0f:66:73:a8'
            frags = [value[i:i + 2] for i in range(0, len(value), 2)]
            return ":".join(frags)


def _table_args():
    engine_name = urlparse.urlparse(CONF.database.connection).scheme
    if engine_name == 'mysql':
        return {
            'mysql_engine': 'InnoDB',
            # No need for UTF8 except specific columns
            'mysql_charset': 'latin1',
            'mysql_collation': 'latin1_general_ci'
        }
    return None


class ProcessionModelBase(object):
    __table_args__ = _table_args()
    __table_initialized__ = False
    # Fields that are required
    _required = ()
    # List of tuples of (field, direction) that results
    # of this model should be sorted by
    _default_order_by = []

    @classmethod
    def get_default_order_by(cls):
        """
        Returns a list of strings that results of this model should
        be sorted by if no sort order was specified.
        """
        return ["{0} {1}".format(f, o) for f, o in cls._default_order_by]

    @classmethod
    def get_primary_key_columns(cls):
        """
        Returns the `sqlalchemy.Column` objects that are the primary key
        for the model.
        """
        return cls.__mapper__.primary_key

    def populate_slug(self, donor, values, max_length=40):
        """
        Populate supplied field values dict with a slugified
        string of the value of the supplied donor field.

        :param donor: String representing the key within kwargs
                      to find the value of the field to use when
                      constructing the slug.
        :param values: Dictionary of fields values to modify. A
                       field with key 'slug' will be added to the
                       dict with a value of the slugified donor field.
        :param max_length: Limit slug length to number of characters.

        :note values parameter is modified in place.

        :raises `ValueError` if donor field is missing from kwargs
        """
        if donor not in values:
            msg = ("No field with key {0} found in supplied "
                   "values. Cannot create slug.").format(donor)
            raise ValueError(msg)

        values.pop('slug', None)
        donor_value = values.get(donor)
        values['slug'] = slugify.slugify(donor_value, max_length=40)

    def get_check_functions(self):
        """
        Generator that yields check functions attached to the
        class.
        """
        for name, method in inspect.getmembers(self, inspect.ismethod):
            if name.startswith('check_'):
                yield method

    def check_required(self, attrs):
        """
        Validation function that looks for required fields.

        :param attrs: dict of possible values to set on the object
        :raises `ValueError` if required fields missing from attrs
        """
        missing = [a for a in self._required
                   if (not attrs.get(a) and getattr(self, a) is None)
                   or (a in attrs.keys() and attrs.get(a) is None)]

        if missing:
            msg = "Required attributes {0} missing from supplied attributes."
            msg = msg.format(', '.join(missing))
            raise ValueError(msg)

    def validate(self, attrs):
        """
        Validation function that accepts a dictionary of attribute
        name/value pairs that are validated and then set on the model.

        This method exists to do sanity-checking on input that
        would go to the database and return errors about non-nullable
        fields in database tables. We avoid issuing a query to the
        database when we know an error would result.

        Subclasses of ProcessModelBase may add additional methods
        that begin with 'check_' to chain validation methods on to
        the set of standard validation methods for required fields and
        other common validation steps. The check methods should raise
        `ValueError` when some attribute fails its check.

        :param attrs: dict of possible values to set on the object
        :raises `ValueError` if required fields missing from attrs
        """
        for fn in self.get_check_functions():
            fn(attrs)


ModelBase = declarative.declarative_base(cls=ProcessionModelBase)


class Organization(ModelBase):
    """
    The world-view of Procession is divided into Organizations,
    Users, and Groups. Organizations are simply containers for Users and other
    Organizations. Groups are containers for Users within an Organization that
    are used for simple categorization of Users. Groups have a set of Roles
    associated with them, and Roles are used to indicate the permissions that
    Users in the Group having that Role are assigned.

    Organizations that have no parent Organization are known as Root
    Organizations. Each Organization has attributes for both a Parent
    Organization as well as the Root Organization to which the Organization
    belongs. This allows us to use both an adjacency list model for quick
    immediate ancestor and immediate descendant queries, as well as a nested
    sets model for more complex queries involving multiple levels of the
    Organization hierarchy.

    We use multiple Root Organizations in order to minimize the impact of
    updates to the Organization hierarchy. Since updating a nested sets model
    is expensive -- since every node in the hierarchy must be updated to
    change the left and right side pointer values -- dividing the whole
    Organization hierarchy into multiple roots allows us to have a nested set
    model per Root Organization, which limits updates to just the Organizations
    within a Root Organization. If we used a single-root tree, with all
    Organizations descendents from a single Organization with no parent, then
    each addition or removal of an Organization would result in the need to
    update every record in the organizations table.
    """
    __tablename__ = 'organizations'
    _required = ('org_name', 'display_name')
    _default_order_by = [
        ('org_name', 'asc'),
    ]
    id = schema.Column(GUID, primary_key=True, default=uuid.uuid4)
    display_name = schema.Column(CoerceUTF8(80))
    org_name = schema.Column(CoerceUTF8(50), nullable=False, unique=True)
    slug = schema.Column(types.String(70), nullable=False, unique=True)
    created_on = schema.Column(types.DateTime,
                               default=datetime.datetime.utcnow)
    deleted_on = schema.Column(types.DateTime)
    root_organization_id = schema.Column(GUID, nullable=False)
    parent_organization_id = schema.Column(GUID, nullable=True, index=True)
    left_sequence = schema.Column(types.Integer, nullable=False)
    right_sequence = schema.Column(types.Integer, nullable=False)
    groups = orm.relationship("OrganizationGroup",
                              backref="root_organization",
                              cascade="all, delete-orphan")

    # Index on (root_organization_id, left_sequence, right_sequence)

    def __init__(self, **kwargs):
        self.populate_slug('org_name', kwargs, max_length=70)
        super(Organization, self).__init__(**kwargs)

    def __str__(self):
        return self.org_name


class OrganizationGroup(ModelBase):
    __tablename__ = 'organization_groups'
    _default_order_by = [
        ('root_organization_id', 'asc'),
        ('group_name', 'asc'),
    ]
    id = schema.Column(GUID, primary_key=True)
    root_organization_id = schema.Column(
        GUID, schema.ForeignKey('organizations.id'))
    display_name = schema.Column(CoerceUTF8(60))
    group_name = schema.Column(CoerceUTF8(30), nullable=False)
    slug = schema.Column(types.String(40), nullable=False)
    created_on = schema.Column(types.DateTime,
                               default=datetime.datetime.utcnow)
    deleted_on = schema.Column(types.DateTime, nullable=True)

    # Unique key on (root_organization_id, group_name)
    # Index on (root_organization, slug)

    def __init__(self, **kwargs):
        self.populate_slug('group_name', kwargs, max_length=70)
        super(Organization, self).__init__(**kwargs)

    def __str__(self):
        return "{0} (root org: {1})".format(
            self.group_name, self.root_organization_id)


class User(ModelBase):
    __tablename__ = 'users'
    _required = ('email', 'user_name', 'display_name')
    _default_order_by = [
        ('created_on', 'desc'),
    ]
    id = schema.Column(GUID, primary_key=True, default=uuid.uuid4)
    display_name = schema.Column(CoerceUTF8(50))
    user_name = schema.Column(CoerceUTF8(30), nullable=False, unique=True)
    slug = schema.Column(types.String(40), nullable=False, unique=True)
    email = schema.Column(types.String(80), nullable=False, unique=True)
    created_on = schema.Column(types.DateTime,
                               default=datetime.datetime.utcnow)
    deleted_on = schema.Column(types.DateTime)
    public_keys = orm.relationship("UserPublicKey", backref="user",
                                   cascade="all, delete-orphan")
    groups = orm.relationship("UserGroupMembership", backref="user",
                              cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        self.populate_slug('user_name', kwargs, max_length=40)
        super(User, self).__init__(**kwargs)

    def __str__(self):
        return "{0} <{1}>".format(self.display_name, self.email)


class UserPublicKey(ModelBase):
    __tablename__ = 'user_public_keys'
    _required = ('fingerprint', 'public_key')
    _default_order_by = [
        ('created_on', 'desc'),
    ]
    user_id = schema.Column(GUID, schema.ForeignKey('users.id'),
                            primary_key=True)
    fingerprint = schema.Column(Fingerprint, primary_key=True)
    public_key = schema.Column(types.Text)
    created_on = schema.Column(types.DateTime,
                               default=datetime.datetime.utcnow)
    deleted_on = schema.Column(types.DateTime, nullable=True)


class UserGroupMembership(ModelBase):
    __tablename__ = 'user_group_memberships'
    user_id = schema.Column(GUID, schema.ForeignKey('users.id'),
                            primary_key=True)
    group_id = schema.Column(GUID, schema.ForeignKey('organization_groups.id'),
                             primary_key=True)


class RepositoryDomain(ModelBase):
    __tablename__ = 'repository_domains'
    _required = ('display_name')
    _default_order_by = [
        ('created_on', 'desc'),
    ]
    id = schema.Column(GUID, primary_key=True, default=uuid.uuid4)
    display_name = schema.Column(types.String(50))
    slug = schema.Column(types.String(50), unique=True, index=True)
    created_on = schema.Column(types.DateTime,
                               default=datetime.datetime.utcnow)
    deleted_on = schema.Column(types.DateTime, nullable=True)
    repositories = orm.relationship("Repository", backref="domain",
                                    cascade="all, delete-orphan")


class Repository(ModelBase):
    __tablename__ = 'repositories'
    _required = ('display_name', 'domain_id')
    _default_order_by = [
        ('created_on', 'desc'),
    ]
    id = schema.Column(GUID, primary_key=True, default=uuid.uuid4)
    domain_id = schema.Column(GUID, schema.ForeignKey('repository_domains.id'))
    display_name = schema.Column(types.String(50))
    created_on = schema.Column(types.DateTime,
                               default=datetime.datetime.utcnow)
    deleted_on = schema.Column(types.DateTime, nullable=True)


class ChangesetStatus(ModelBase):
    __tablename__ = 'changeset_status'
    _required = ('name')
    id = schema.Column(types.Integer, primary_key=True)
    name = schema.Column(types.String(12), unique=True, index=True)
    desc = schema.Column(types.Text)


class Changeset(ModelBase):
    __tablename__ = 'changesets'
    _required = ('repo_id', 'target_branch', 'uploaded_by', 'commit_message')
    _default_order_by = [
        ('created_on', 'desc'),
    ]
    id = schema.Column(GUID, primary_key=True)
    repo_id = schema.Column(GUID, schema.ForeignKey('repositories.id'))
    target_branch = schema.Column(types.String(200))
    status_id = schema.Column(types.Integer,
                              schema.ForeignKey('changeset_status.id'))
    uploaded_by = schema.Column(GUID, schema.ForeignKey('users.id'))
    commit_message = schema.Column(types.Text)
    created_on = schema.Column(types.DateTime,
                               default=datetime.datetime.utcnow)
    deleted_on = schema.Column(types.DateTime, nullable=True)
    changes = orm.relationship("Change", backref="changeset",
                               cascade="all, delete-orphan")


class Change(ModelBase):
    __tablename__ = 'changes'
    _required = ('changeset_id', 'uploaded_by')
    _default_order_by = [
        ('created_on', 'desc'),
    ]
    changeset_id = schema.Column(GUID, schema.ForeignKey('changesets.id'),
                                 primary_key=True)
    sequence = schema.Column(types.Integer, primary_key=True)
    uploaded_by = schema.Column(GUID, schema.ForeignKey('users.id'))
    created_on = schema.Column(types.DateTime,
                               default=datetime.datetime.utcnow)
    deleted_on = schema.Column(types.DateTime, nullable=True)


ModelBase.metadata.create_all(session.get_engine())
