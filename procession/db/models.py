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

    @classmethod
    def attribute_names(cls):
        """
        Helper method that returns the names of the attributes of
        the model that are direct table columns (i.e. no relations)
        """
        return [
            prop.key for prop
            in orm.class_mapper(cls).iterate_properties
            if isinstance(prop, orm.ColumnProperty)
        ]

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

    def to_dict(self):
        """
        Returns a dict containing the model's fields. Only the model's
        fields are used as keys in the dict. No relationships are followed
        or eagerly loaded.
        """
        res = dict()
        for attr in self.attribute_names():
            res[attr] = getattr(self, attr)
        return res


ModelBase = declarative.declarative_base(cls=ProcessionModelBase)


class User(ModelBase):
    __tablename__ = 'users'
    _required = ('email', 'display_name')
    _default_order_by = [
        ('created_on', 'desc'),
    ]
    id = schema.Column(GUID, primary_key=True, default=uuid.uuid4)
    display_name = schema.Column(CoerceUTF8(50), nullable=False)
    email = schema.Column(types.String(80), nullable=False, unique=True)
    created_on = schema.Column(types.DateTime,
                               default=datetime.datetime.utcnow)
    deleted_on = schema.Column(types.DateTime)
    public_keys = orm.relationship("UserPublicKey", backref="user",
                                   cascade="all, delete, delete-orphan")
    groups = orm.relationship("UserGroupMembership", backref="user",
                              cascade="all, delete, delete-orphan")

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


class UserGroup(ModelBase):
    __tablename__ = 'user_groups'
    _default_order_by = [
        ('created_on', 'desc'),
    ]
    id = schema.Column(GUID, primary_key=True)
    display_name = schema.Column(types.String(50))
    created_on = schema.Column(types.DateTime,
                               default=datetime.datetime.utcnow)
    deleted_on = schema.Column(types.DateTime, nullable=True)


class UserGroupMembership(ModelBase):
    __tablename__ = 'user_group_memberships'
    user_id = schema.Column(GUID, schema.ForeignKey('users.id'),
                            primary_key=True)
    group_id = schema.Column(GUID, schema.ForeignKey('user_groups.id'),
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
                                    cascade="all, delete, delete-orphan")


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
                               cascade="all, delete, delete-orphan")


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


class AuditLog(ModelBase):
    __tablename__ = 'audit_log'
    _required = ('taken_by', 'action')
    _default_order_by = [
        ('occurred_on', 'desc'),
    ]
    id = schema.Column(types.Integer, primary_key=True)
    taken_by = schema.Column(GUID, schema.ForeignKey('users.id'), index=True)
    occurred_on = schema.Column(types.DateTime,
                                default=datetime.datetime.utcnow,
                                index=True)
    action = schema.Column(types.String(50), index=True)
    record = schema.Column(types.Text)
    # Set of valid actions that may be audited. Changeset and related
    # activity we don't feel is audit-worthy, as Git itself keeps track
    # of source-control-related changes.
    __actions__ = (
        'user_create',
        'user_delete',
        'user_modify',
        'user_membership_modify',
        'repository_create',
        'repository_delete',
        'repository_modify'
    )


ModelBase.metadata.create_all(session.get_engine())
