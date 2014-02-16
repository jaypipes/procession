# -*- encoding: utf-8 -*-
#
# Copyright 2013-2014 Jay Pipes
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
import sqlalchemy
from sqlalchemy import orm
from sqlalchemy import schema
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext import declarative
from sqlalchemy.sql import expression as expr

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
        if dialect.name == 'postgresql':  # pragma: no cover
            return dialect.type_descriptor(postgresql.UUID())
        else:
            return dialect.type_descriptor(types.CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)  # pragma: no cover
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
            return value  # pragma: no cover
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
            return value  # pragma: no cover
        else:
            # go from '435143a1b5fc8bb70a3aa9b10f6673a8'
            # to '43:51:43:a1:b5:fc:8b:b7:0a:3a:a9:b1:0f:66:73:a8'
            frags = [value[i:i + 2] for i in range(0, len(value), 2)]
            return ":".join(frags)


def _table_args():
    engine_name = urlparse.urlparse(CONF.database.connection).scheme
    if engine_name == 'mysql':
        return {  # pragma: no cover
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

    def has_field_changed(self, field):
        """
        Returns True if the specified field has changed values, False
        otherwise.
        """
        inspected = sqlalchemy.inspect(self).attrs
        field_history = getattr(inspected, field).history
        return field_history.has_changes()

    def has_any_field_changed(self, *fields):
        """
        Returns True if any of the specifieds field has changed values,
        False otherwise.
        """
        return any([self.has_field_changed(f) for f in fields])

    def set_slug(self):
        """
        Populates the slug attribute of the model by looking at the
        fields listed in the class' _slug_from attribute and constructing
        the slug value from the value of those fields.
        """
        slug_fields = getattr(self, '_slug_from')
        assert slug_fields is not None

        subject = ' '.join([str(getattr(self, f, '')) for f in slug_fields])
        this_table = self.__table__
        slug_col_len = this_table.c.slug.type.length
        self.slug = slugify.slugify(subject, max_length=slug_col_len)

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
    __table_args__ = (
        ModelBase.__table_args__,
        schema.UniqueConstraint('org_name', 'parent_organization_id',
                                name="uc_org_name_in_root"),
        schema.UniqueConstraint('root_organization_id', 'left_sequence',
                                'right_sequence', name="uc_nested_set_shard")
    )
    _required = ('org_name', 'display_name')
    _default_order_by = [
        ('slug', 'asc'),
    ]
    id = schema.Column(GUID, primary_key=True, default=uuid.uuid4)
    display_name = schema.Column(CoerceUTF8(50))
    org_name = schema.Column(CoerceUTF8(30))
    slug = schema.Column(types.String(100), unique=True)
    created_on = schema.Column(types.DateTime,
                               default=datetime.datetime.utcnow)
    # NOTE(jaypipes): We don't index root_organization_id separately
    #                 because it is the left-most column in the unique
    #                 constraint on:
    #                 (root_org_id, left_sequence, right_sequence)
    #                 and therefore functions as a single-column index
    #                 on root_organization_id.
    root_organization_id = schema.Column(GUID)
    parent_organization_id = schema.Column(GUID, nullable=True, index=True)
    left_sequence = schema.Column(types.Integer)
    right_sequence = schema.Column(types.Integer)
    groups = orm.relationship("Group",
                              backref="root_organization",
                              cascade="all, delete-orphan")

    def set_slug(self, **kwargs):
        """
        The slug for an organization is a bit different from other models
        because of the sharded hierarchical layout of the organization trees.

        We have a unique constraint on (org_name, parent_organization_id),
        which will prevent sub-organizations that have the same parent from
        sharing an organization name. In addition, for nodes without a parent
        (top-level root organizations), the (org_name, NULL) unique constraint
        will prevent top-level root organizations from having the same name.

        Now, to generate the slug for an organization, we prepend the parent
        organization's slug onto this organization's slug, with a hyphen
        separator. This ensures that the slug is unique within the entire
        set of organizations. It also means we only need to grab the parent
        organization's slug, not the slug of all ascendants from this
        organization.

        :param kwargs: optional keywords arguments to the function:

            `session`: A session object to use
        """
        sess = kwargs.get('session', session.get_session())
        conn = sess.connection()
        org_table = self.__table__
        slug_col_len = org_table.c.slug.type.length
        slug_prefix = ''
        if self.parent_organization_id is not None:
            where_expr = org_table.c.id == self.parent_organization_id
            sel = expr.select([org_table.c.slug]).where(where_expr)
            parent = conn.execute(sel).fetchone()
            slug_prefix = parent[0] + '-'
        to_slug = slug_prefix + self.org_name
        self.slug = slugify.slugify(to_slug, max_length=slug_col_len)


class Group(ModelBase):
    __tablename__ = 'groups'
    __table_args__ = (
        ModelBase.__table_args__,
        schema.UniqueConstraint('root_organization_id', 'group_name',
                                name='uc_root_org_group_name')
    )
    _required = ('group_name', 'display_name', 'root_organization_id')
    _default_order_by = [
        ('root_organization_id', 'asc'),
        ('group_name', 'asc'),
    ]
    id = schema.Column(GUID, primary_key=True)
    root_organization_id = schema.Column(
        GUID, schema.ForeignKey('organizations.id', ondelete='CASCADE'))
    display_name = schema.Column(CoerceUTF8(60))
    group_name = schema.Column(CoerceUTF8(30))
    slug = schema.Column(types.String(40), unique=True, index=True)
    created_on = schema.Column(types.DateTime,
                               default=datetime.datetime.utcnow)
    users = orm.relationship("UserGroupMembership", backref="group",
                             cascade="all, delete-orphan")

    def set_slug(self, **kwargs):
        """
        Sets the slug for the group.

        Because the group name is not unique (only unique within an
        organization tree, the slug for an organization group is the
        combination of the group's root organization slug and the
        group name.

        We have a unique constraint on (group_name, root_organization_id),
        which will prevent organization trees from having more than one
        group with the same name.

        :param kwargs: optional keywords arguments to the function:

            `session`: A session object to use
        """
        sess = kwargs.get('session', session.get_session())
        conn = sess.connection()
        group_table = self.__table__
        org_table = Organization.__table__
        slug_col_len = group_table.c.slug.type.length
        slug_prefix = ''
        where_expr = org_table.c.id == self.root_organization_id
        sel = expr.select([org_table.c.slug]).where(where_expr)
        root = conn.execute(sel).fetchone()
        slug_prefix = root[0] + '-'
        to_slug = slug_prefix + self.group_name
        self.slug = slugify.slugify(to_slug, max_length=slug_col_len)


class User(ModelBase):
    __tablename__ = 'users'
    _required = ('email', 'user_name', 'display_name')
    _slug_from = ('user_name',)
    _default_order_by = [
        ('created_on', 'desc'),
    ]
    id = schema.Column(GUID, primary_key=True, default=uuid.uuid4)
    display_name = schema.Column(CoerceUTF8(50))
    user_name = schema.Column(CoerceUTF8(30), unique=True)
    slug = schema.Column(types.String(40), unique=True)
    email = schema.Column(types.String(80), unique=True)
    created_on = schema.Column(types.DateTime,
                               default=datetime.datetime.utcnow)
    public_keys = orm.relationship("UserPublicKey", backref="user",
                                   cascade="all, delete-orphan")
    groups = orm.relationship("UserGroupMembership", backref="user",
                              cascade="all, delete-orphan")

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


class UserGroupMembership(ModelBase):
    __tablename__ = 'user_group_memberships'
    user_id = schema.Column(GUID, schema.ForeignKey('users.id'),
                            primary_key=True)
    group_id = schema.Column(GUID, schema.ForeignKey('groups.id'),
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


ModelBase.metadata.create_all(session.get_engine())
