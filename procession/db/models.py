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
    engine_name = 'TODO'
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

    def get_earliest_value(self, field):
        """
        Returns the earliest value of the field from the field history.
        """
        inspected = sqlalchemy.inspect(self).attrs
        field_history = getattr(inspected, field).history
        deletes = field_history[2]
        if len(deletes) > 0:
            return deletes[0]
        return None  # pragma: no cover

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
        schema.UniqueConstraint('name', 'parent_organization_id',
                                name="uc_name_in_org_tree"),
        # NOTE(jaypipes): Note that this is not a UniqueConstraint because of
        # the special root_organization_id column. This column is set to zero
        # when a new organization is created. Immediately after the create, the
        # root_organization_id is then set to the integer sequence that is set
        # on the id column. Because there is a chance that two organization
        # records could be created in quick succession, both with a temporary
        # root_organization_id of zero, which would violate the unique
        # constraint.
        schema.Index('uc_nested_set_shard', 'root_organization_id',
                     'left_sequence', 'right_sequence'),
        schema.Index('ix_parent_organization', 'parent_organization_id'),
        ModelBase.__table_args__,
    )
    _required = ('name', 'display_name')
    _default_order_by = [
        ('slug', 'asc'),
    ]
    id = schema.Column(types.Integer, primary_key=True)
    display_name = schema.Column(CoerceUTF8(50), nullable=False)
    name = schema.Column(CoerceUTF8(30), nullable=False)
    slug = schema.Column(types.String(100), nullable=False,
                         unique=True, index=True)
    created_on = schema.Column(types.DateTime, nullable=False,
                               default=datetime.datetime.utcnow)
    root_organization_id = schema.Column(types.Integer, nullable=False)
    parent_organization_id = schema.Column(types.Integer, nullable=True)
    left_sequence = schema.Column(types.Integer, nullable=False)
    right_sequence = schema.Column(types.Integer, nullable=False)
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
        org_table = self.__table__
        slug_col_len = org_table.c.slug.type.length
        slug_prefix = ''
        if self.parent_organization_id is not None:
            sess = kwargs.get('session', session.get_session())
            conn = sess.connection()
            where_expr = org_table.c.id == self.parent_organization_id
            sel = expr.select([org_table.c.slug]).where(where_expr)
            parent = conn.execute(sel).fetchone()
            slug_prefix = parent[0] + '-'
        to_slug = slug_prefix + self.name
        self.slug = slugify.slugify(to_slug, max_length=slug_col_len)

    def __repr__(self):
        return "<Org {0} '{1}'>".format(self.id, self.name)


class Group(ModelBase):
    __tablename__ = 'groups'
    __table_args__ = (
        schema.UniqueConstraint('root_organization_id', 'name',
                                name='uc_root_org_name'),
        ModelBase.__table_args__,
    )
    _required = ('name', 'display_name', 'root_organization_id')
    _default_order_by = [
        ('root_organization_id', 'asc'),
        ('name', 'asc'),
    ]
    id = schema.Column(types.Integer, primary_key=True)
    root_organization_id = schema.Column(
        types.Integer, schema.ForeignKey('organizations.id',
                                         onupdate="CASCADE",
                                         ondelete="CASCADE"),
        nullable=False)
    display_name = schema.Column(CoerceUTF8(60), nullable=False)
    name = schema.Column(CoerceUTF8(30), nullable=False)
    slug = schema.Column(types.String(100), nullable=False,
                         unique=True, index=True)
    created_on = schema.Column(types.DateTime, nullable=False,
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
        to_slug = slug_prefix + self.name
        self.slug = slugify.slugify(to_slug, max_length=slug_col_len)

    def __repr__(self):
        res = "<Group {0} '{1}' (in Org: {2})>"
        return res.format(self.id, self.name, self.root_organization_id)


class User(ModelBase):
    __tablename__ = 'users'
    _required = ('email', 'name', 'display_name')
    _slug_from = ('name',)
    _default_order_by = [
        ('created_on', 'desc'),
    ]
    id = schema.Column(types.Integer, primary_key=True)
    display_name = schema.Column(CoerceUTF8(50), nullable=False)
    name = schema.Column(CoerceUTF8(30), nullable=False,
                         unique=True, index=True)
    slug = schema.Column(types.String(40), nullable=False,
                         unique=True, index=True)
    email = schema.Column(types.String(80), nullable=False,
                          unique=True, index=True)
    created_on = schema.Column(types.DateTime, nullable=False,
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
    user_id = schema.Column(types.Integer,
                            schema.ForeignKey('users.id',
                                              onupdate="CASCADE",
                                              ondelete="CASCADE"),
                            primary_key=True)
    fingerprint = schema.Column(Fingerprint, primary_key=True)
    public_key = schema.Column(types.Text, nullable=False)
    created_on = schema.Column(types.DateTime, nullable=False,
                               default=datetime.datetime.utcnow)


class UserGroupMembership(ModelBase):
    __tablename__ = 'user_group_memberships'
    user_id = schema.Column(types.Integer,
                            schema.ForeignKey('users.id',
                                              onupdate="CASCADE",
                                              ondelete="CASCADE"),
                            primary_key=True)
    group_id = schema.Column(types.Integer,
                             schema.ForeignKey('groups.id',
                                               onupdate="CASCADE",
                                               ondelete="CASCADE"),
                             primary_key=True)


class Domain(ModelBase):
    """
    The repository domain is a single-level container for SCM repositories
    under Procession's control. There is no nesting or hierarchy involved
    here. It is a way to segregate collections of repositories, nothing
    more. Organizations and groups -- and the associated membership in them
    for users -- are how access to any repository (or repository domain)
    is handled.

    Note that every repository added to Procession must belong to a domain.
    If a repository is added to Procession and a domain is not specified,
    Procession creates a domain named the same as the user that is adding
    the repository.

    In this way, the layout of repositories and domains matches GitHub's
    concept of a repository, which can be either in a user's personal scope
    -- e.g http://github.com/jaypipes/procession -- or in a GitHub
    organization's scope -- e.g. http://github.com/procession/procession.

    We feel this is an adequate and efficient way to organize SCM
    repositories, and the more flexible and complex org -> group -> user
    hierarchy is the most efficient and functional way to handle access
    control to the repositories and repository domains.
    """
    __tablename__ = 'domains'
    _required = ('name', 'owner_id')
    _slug_from = ('name',)
    _default_order_by = [
        ('slug', 'asc'),
    ]

    VISIBILITY_ALL = 1
    """The domain is visible to anyone"""

    VISIBILITY_RESTRICTED = 2
    """The domain is visible to the owner and anyone the owner shares with"""

    id = schema.Column(types.Integer, primary_key=True)
    name = schema.Column(CoerceUTF8(50), nullable=False)
    slug = schema.Column(types.String(60), nullable=False, unique=True,
                         index=True)
    created_on = schema.Column(types.DateTime, nullable=False,
                               default=datetime.datetime.utcnow)
    visibility = schema.Column(types.Integer, nullable=False,
                               default=VISIBILITY_ALL)
    owner_id = schema.Column(types.Integer,
                             schema.ForeignKey('users.id',
                                               onupdate="CASCADE",
                                               ondelete="CASCADE"),
                             nullable=False)
    repositories = orm.relationship("Repository", backref="domain",
                                    cascade="all, delete-orphan")

    def __str__(self):
        return "{0} <{1}>".format(self.id, self.name)


class Repository(ModelBase):
    """
    Basic information about an SCM repository. Each repo belongs to one
    domain. Although repositories have a unique identifier, they are
    most commonly referred to with the domain and repo name. Note that
    the SCM software itself is the source of truth about repository details.
    The only information we store in the database about the repo is
    meta-information regarding the organization of the repository, which
    is used in ACL operations.
    """
    __tablename__ = 'repositories'
    __table_args__ = (
        schema.UniqueConstraint('domain_id', 'name',
                                name='uc_domain_name'),
        ModelBase.__table_args__,
    )
    _required = ('name', 'domain_id')
    _default_order_by = [
        ('created_on', 'desc'),
    ]
    id = schema.Column(types.Integer, primary_key=True)
    domain_id = schema.Column(types.Integer,
                              schema.ForeignKey('domains.id',
                                                onupdate="CASCADE",
                                                ondelete="CASCADE"),
                              nullable=False)
    name = schema.Column(CoerceUTF8(50), nullable=False)
    owner_id = schema.Column(types.Integer,
                             schema.ForeignKey('users.id',
                                               onupdate="CASCADE",
                                               ondelete="CASCADE"),
                             nullable=False)
    created_on = schema.Column(types.DateTime, nullable=False,
                               default=datetime.datetime.utcnow, index=True)

    def __str__(self):
        return "{0} <{1}, domain: {2}>".format(self.id, self.name,
                                               self.domain_id)


class Changeset(ModelBase):
    """
    Represents code that has been proposed for merging into a target branch.
    The changeset has a state, which is a fixed integer value representing
    the status of the changeset in relation to the target branch. Each
    changeset targets one and only one repository.
    """
    __tablename__ = 'changesets'
    __table_args__ = (
        schema.Index('ix_repo_id_state', 'target_repo_id', 'state'),
        schema.Index('ix_uploaded_by_repo_id_state', 'uploaded_by',
                     'target_repo_id', 'state'),
        ModelBase.__table_args__,
    )
    _required = ('target_repo_id', 'target_branch', 'uploaded_by',
                 'commit_message')
    _default_order_by = [
        ('created_on', 'desc'),
    ]
    STATE_ABANDONED = 0
    """
    A state that means the owner of the changeset has given up on the code and
    does not want it to be shown in any active lists of changesets
    """
    STATE_DRAFT = 1
    """
    A state that means the owner has pushed the changeset up for review but is
    indicating that the code is a work in progress
    """
    STATE_ACTIVE = 5
    """A state indicating the changeset is currently under review"""
    STATE_CLEARED = 8
    """
    A state that means the changeset has met all conditions needed to merge
    the code into the target branch, but the SCM system has yet to merge the
    branch
    """
    STATE_MERGED = 12
    """A state indicating the code has been merged into the target branch"""

    id = schema.Column(types.Integer, primary_key=True)
    target_repo_id = schema.Column(types.Integer,
                                   schema.ForeignKey('repositories.id',
                                                     onupdate="CASCADE",
                                                     ondelete="CASCADE"),
                                   nullable=False)
    target_branch = schema.Column(types.String(200), nullable=False)
    state = schema.Column(types.Integer, nullable=False)
    uploaded_by = schema.Column(types.Integer,
                                schema.ForeignKey('users.id',
                                                  onupdate="CASCADE",
                                                  ondelete="CASCADE"),
                                nullable=False)
    commit_message = schema.Column(types.Text)
    created_on = schema.Column(types.DateTime, nullable=False,
                               default=datetime.datetime.utcnow)
    changes = orm.relationship("Change", backref="changeset",
                               cascade="all, delete-orphan")

    def __str__(self):
        return "{0} <target_repo: {1}>".format(self.id, self.target_repo_id)


class Change(ModelBase):
    """
    A Change is a code or commit message modification of a Changeset. Within
    a Changeset, each Change is identified by a sequence number starting at 1.
    """
    __tablename__ = 'changes'
    __table_args__ = (
        schema.Index('ix_uploaded_by_changeset_id', 'uploaded_by',
                     'changeset_id'),
        ModelBase.__table_args__,
    )
    _required = ('changeset_id', 'uploaded_by')
    _default_order_by = [
        ('created_on', 'desc'),
    ]
    changeset_id = schema.Column(types.Integer,
                                 schema.ForeignKey('changesets.id',
                                                   onupdate="CASCADE",
                                                   ondelete="CASCADE"),
                                 primary_key=True)
    sequence = schema.Column(types.Integer, primary_key=True)
    uploaded_by = schema.Column(types.Integer,
                                schema.ForeignKey('users.id',
                                                  onupdate="CASCADE",
                                                  ondelete="CASCADE"),
                                nullable=False)
    created_on = schema.Column(types.DateTime, nullable=False,
                               default=datetime.datetime.utcnow)
