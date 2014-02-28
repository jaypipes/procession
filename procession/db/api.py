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

"""
Defines the internal API for procession's database. This is an internal
API and may change at any time. If you are looking for a stable API to
community with Procession, use the public REST API or alternately, use
the python-processionclient's public Python API.

One to Many Relation CRUD operations
====================================

Models defined in `procession.db.models` that are the parents or children
in one-to-many relationships will have a set of methods in this module for
doing CRUD operations on the model:

    * $MODELs_get --> Returns a list of MODEL objects
    * $MODEL_get_by_pk --> Return a MODEL object, may raise NotFound
    * $MODEL_create --> Create a new MODEL object, may raise Duplicate
    * $MODEL_update --> Update an existing MODEL object, may raise NotFound
    * $MODEL_delete --> Delete an existing MODEL object, may raise NotFound

Many to Many Relation CRUD operations
=====================================

For models that represent a many-to-many relationship, such as
`procession.db.models.UserGroupMembership`, this module will contain methods
for fetching either side of the relation:

    * $MODELA_$MODELBs_get --> Returns a list of MODELB objects having a
      a MODELA relationship
    * $MODELB_$MODELAs_get --> Returns a list of MODELA objects having a
      a MODELB relationship

In addition, there will also be methods to control the relationship mapping
table, but **only for one side of the mapping**:

    * $MODELA_$MODELB_add --> Adds a mapping of MODELA and MODELB,
      may raise NotFound for either MODELA or MODELB.
    * $MODELA_$MODELB_remove --> Removes an existing mapping for MODELA and
      MODELB, may raise NotFound for either MODELA or MODELB

So, for example, the following methods exist to control the membership of
a user in one or more groups:

    * user_groups_get --> Returns a list of group objects for a user
    * group_users_get --> Returns a list of user objects for a group
    * user_group_add --> Adds a user and group to the mapping table
    * user_group_remove --> Removes a user and group from the mapping table

However, there will be no methods called "group_user_add" or
"group_user_remove".
"""

import functools
import logging
import uuid

from oslo.config import cfg
import sqlalchemy
from sqlalchemy import exc as sa_exc
from sqlalchemy.orm import exc as sao_exc
from sqlalchemy.sql import expression as expr

from procession import exc
from procession import helpers
from procession.db import models
from procession.db import session

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def if_slug_get_pk(model):
    """
    Decorator for a function that looks up a model object
    by primary key, but the model also has a slug attribute.
    If the supplied primary key value looks like a UUID, then the
    decorator simply calls the decorated function as-is. If
    the supplied primary key value does *not* look like a UUID,
    then the primary key value is presumed to be a slug, in which
    case we try to look up the actual primary key of the model by
    querying for the slug.

    :param model: the model to query on (either fully-qualified string
                  or a model class object
    :raises `procession.exc.NotFound` if slug isn't found
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            ctx = args[0]
            pk_or_slug = str(args[1])
            if not helpers.is_like_uuid(pk_or_slug):
                # Slug fields are only on models that have a single-column
                # primary key, so we just grab the first of the list here.
                pk_col = model.get_primary_key_columns()[0]
                sess = kwargs.get('session', session.get_session())
                try:
                    real_pk_value = sess.query(pk_col).filter(
                        model.slug == pk_or_slug).one()
                    return f(ctx, real_pk_value.id, *args[2:], **kwargs)
                except sao_exc.NoResultFound:
                    msg = ("An object with slug {0} "
                           "was not found.").format(pk_or_slug)
                    raise exc.NotFound(msg)
            return f(*args, **kwargs)
        return wrapper
    return decorator


def organizations_get(ctx, spec, **kwargs):
    """
    Gets organization models based on one or more search criteria.

    :param ctx: `procession.context.Context` object
    :param spec: `procession.api.SearchSpec` object that contains filters,
                 ordering, limits, etc
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use

    :raises `procession.exc.BadInput` if marker record not found
    :raises `ValueError` if search arguments didn't make sense
    :returns list of `procession.db.models.Organization` objects
    """
    sess = kwargs.get('session', session.get_session())
    return _get_many(sess, models.Organization, spec)


@if_slug_get_pk(models.Organization)
def organization_get_by_pk(ctx, org_id, **kwargs):
    """
    Convenience wrapper for common get by ID

    :param ctx: `procession.context.Context` object
    :param org_id: Organization ID to look up
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use

    :raises `procession.exc.NotFound` if no org found matching
            search arguments
    :returns `procession.db.models.Organization` object that was created
    """
    sess = kwargs.get('session', session.get_session())
    sargs = dict(id=org_id)
    return _get_one(sess, models.Organization, **sargs)


def organization_get_subtree(ctx, parent_org_id, **kwargs):
    """
    Returns a set of Organization objects representing the subtree
    with the supplied parent org as its top-most parent.

    For example, assume that orgs A, B, C, D, E, and F are all in the
    same root organization, and arranged like so:

                                    A
                                /       \
                            B               C
                          /   \           /   \
                        D       E       F       G

    Calling this function with parent_org_id of B would produce a
    `sqlalchemy.sql.orm.Query` object that contained organizations
    B, D, and E.

    We use a nested sets model query construct to perform the operation.

    :param ctx: `procession.context.Context` object
    :param parent_org_id: ID of the org that is the top parent of the tree to
                          return.
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use
        `root_organization_id`: Optional. If not found, we look up the root
                                organization from the parent organization.

    :returns list of `procession.db.models.Organization` objects
    """
    sess = kwargs.get('session', session.get_session())
    conn = sess.connection()

    o_self = models.Organization.__table__.alias('o_self')
    o_parent = models.Organization.__table__.alias('o_parent')

    # Nested sets allows us to find a parent-inclusive tree by using the
    # following SELECT expression:
    #   SELECT o_self.* FROM organizations o_self
    #   INNER JOIN organizations o_parent
    #   ON o_self.left_sequence
    #   BETWEEN o_parent.left_sequence AND o_parent.right_sequence
    #   AND o_parent.root_organization_id = :root_org_id
    #   AND o_parent = :parent_org_id
    #   WHERE o_self.root_organization_id = :root_org_id

    sel = expr.select([o_self]).where(
        expr.and_(
            o_self.c.left_sequence >= o_parent.c.left_sequence,
            o_self.c.left_sequence <= o_parent.c.right_sequence,
            o_parent.c.id == parent_org_id,
            o_self.c.root_organization_id == o_parent.c.root_organization_id
        )
    )
    return conn.execute(sel).fetchall()


def organization_create(ctx, attrs, **kwargs):
    """
    Creates an organization in the database. The session (either
    supplied or auto-created) is always committed upon successful
    creation.

    :param ctx: `procession.context.Context` object
    :param attrs: dict with information about the org to create
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use

    :raises `procession.exc.Duplicate` if org name already found
    :raises `ValueError` if validation of inputs fails
    :raises `TypeError` if unknown attribute is supplied
    :returns `procession.db.models.Organization` object that was created
    """
    sess = kwargs.get('session', session.get_session())

    o = models.Organization(**attrs)
    o.validate(attrs)

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


def organization_delete(ctx, org_id, **kwargs):
    """
    Deletes an organization from the database. All child regions
    are deleted as well, as are all groups and domains associated with the
    organization.

    :param ctx: `procession.context.Context` object
    :param org_id: ID of the organization to delete
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use

    :raises `procession.exc.NotFound` if organization ID was not found.
    :raises `procession.exc.BadInput` if organization ID was not a UUID.
    """
    sess = kwargs.get('session', session.get_session())

    try:
        o = sess.query(models.Organization).filter(
            models.Organization.id == org_id).one()
        _delete_organization_from_tree(ctx, o, session=sess)
        #NOTE(jaypipes): When issuing a DELETE expression not through the
        #                SQLAlchemy session, the foreign key relations are
        #                not cascaded, so we must do it manually here.
        conn = sess.connection()
        ugm_tab = models.UserGroupMembership.__table__
        group_tab = models.Group.__table__

        conn = sess.connection()
        where_expr = group_tab.c.root_organization_id == org_id
        groups_sel = expr.select([group_tab.c.id]).where(where_expr)
        groups_sel = groups_sel.distinct()
        groups = conn.execute(groups_sel).fetchall()
        if len(groups) > 0:
            conn = sess.connection()
            groups = [g[0] for g in groups]
            deleter = ugm_tab.delete(ugm_tab.c.group_id.in_(groups))
            conn.execute(deleter)

        conn = sess.connection()
        deleter = group_tab.delete(group_tab.c.root_organization_id == org_id)
        conn.execute(deleter)

        LOG.info("Deleted organization with ID {0} and all "
                 "descendants.".format(org_id))
    except sao_exc.NoResultFound:
        msg = "An organization with ID {0} was not found.".format(org_id)
        raise exc.NotFound(msg)
    except sa_exc.StatementError:
        msg = "Organization ID {0} was badly formatted.".format(org_id)
        raise exc.BadInput(msg)


def _insert_organization_into_tree(ctx, org, **kwargs):
    """
    Updates the nested sets hierarchy for a new organization within
    the database. We use a slightly different algorithm for inserting
    a new organization that has a parent with no other children than
    when the new organization's parent already has children.

    In short, we use the following basic methodology:

    @rgt, @lft, @has_children = SELECT right_sequence, left_sequence,
                                 (SELECT COUNT(*) FROM organizations
                                  WHERE parent_organization_id = parent_org_id)
                                FROM organizations
                                WHERE id = parent_org_id;

    if @has_children:
        UPDATE organizations SET right_sequence = right_sequence + 2
        WHERE right_sequence > @rgt
        AND root_organization_id = root_org_id;
        UPDATE organizations SET left_sequence = left_sequence + 2
        WHERE left_sequence > @rgt
        AND root_organization_id = root_org_id;
        set org.left_sequence = @rgt + 1;
        set org.right_sequence = @rgt + 2;
    else:
        UPDATE organizations SET right_sequence = right_sequence + 2
        WHERE right_sequence > @lft
        AND root_organization_id = root_org_id;
        UPDATE organizations SET left_sequence = left_sequence + 2
        WHERE left_sequence > @lft
        AND root_organization_id = root_org_id;
        set org.left_sequence = @lft + 1;
        set org.right_sequence = @lft + 2;

    :param ctx: `procession.context.Context` object
    :param org: Organization model to update
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use
    """
    sess = kwargs.get('session', session.get_session())
    conn = sess.connection()

    org_table = models.Organization.__table__
    root_org_id = org.root_organization_id
    parent_org_id = org.parent_organization_id

    # We lock the entire root organization tree in the database here,
    # since we'll be updating the left and right sequences of a large number
    # of records within the the root organization tree.
    with sess.begin(subtransactions=True):

        LOG.debug("Locking records in root organization {0} in preparation "
                  "for tree insertion.".format(root_org_id))
        sess.query(models.Organization).filter_by(
            root_organization_id=root_org_id).with_lockmode('update')

        sq_where_expr = org_table.c.parent_organization_id == parent_org_id
        count_subquery = expr.select([sqlalchemy.func.count(org_table.c.id)])
        count_subquery = count_subquery.where(sq_where_expr)
        where_expr = org_table.c.id == parent_org_id
        sel = expr.select([org_table.c.left_sequence,
                           org_table.c.right_sequence,
                           count_subquery.as_scalar()]).where(where_expr)
        row = conn.execute(sel).fetchone()
        lft, rgt, num_children = row

        LOG.debug("Inserting new organization into root "
                  "org tree {0}. Prior to insertion, new org's parent {1} "
                  "has left of {2}, right of {3}, and {4} children.".format(
                  root_org_id, parent_org_id, lft, rgt, num_children))

        if num_children > 0:
            stmt = org_table.update().where(
                org_table.c.right_sequence > rgt).where(
                    org_table.c.root_organization_id == root_org_id).values(
                        right_sequence=org_table.c.right_sequence + 2)
            conn.execute(stmt)
            stmt = org_table.update().where(
                org_table.c.left_sequence > rgt).where(
                    org_table.c.root_organization_id == root_org_id).values(
                        left_sequence=org_table.c.left_sequence + 2)
            conn.execute(stmt)
            org.left_sequence = rgt + 1
            org.right_sequence = rgt + 2
        else:
            stmt = org_table.update().where(
                org_table.c.right_sequence > lft).where(
                    org_table.c.root_organization_id == root_org_id).values(
                        right_sequence=org_table.c.right_sequence + 2)
            conn.execute(stmt)
            stmt = org_table.update().where(
                org_table.c.left_sequence > lft).where(
                    org_table.c.root_organization_id == root_org_id).values(
                        left_sequence=org_table.c.left_sequence + 2)
            conn.execute(stmt)
            org.left_sequence = lft + 1
            org.right_sequence = lft + 2


def _delete_organization_from_tree(ctx, org, **kwargs):
    """
    Updates the nested sets hierarchy when an organization is removed
    from an organization tree.

    In short, we use the following basic methodology:

    @rgt, @lft = SELECT right_sequence, left_sequence
                 FROM organizations
                 WHERE id = org_id;
    @width = @rgt - @lft + 1

    DELETE FROM organizations
    WHERE left_sequence BETWEEN @lft and @rgt;
    AND root_organization = root_org_id
    UPDATE organizations SET right_sequence = right_sequence - @width
    WHERE right_sequence > @rgt
    AND root_organization_id = root_org_id;
    UPDATE organizations SET left_sequence = left_sequence - @width
    WHERE left_sequence > @rgt
    AND root_organization_id = root_org_id;

    :param ctx: `procession.context.Context` object
    :param org: Organization model to update
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use
    """
    sess = kwargs.get('session', session.get_session())
    conn = sess.connection()

    org_table = models.Organization.__table__
    root_org_id = org.root_organization_id

    # We lock the entire root organization tree in the database here,
    # since we'll be updating the left and right sequences of a large number
    # of records within the the root organization tree as well as removing
    # a number of records from the tree.
    with sess.begin(subtransactions=True):

        LOG.debug("Locking records in root organization {0} in preparation "
                  "for tree element deletion.".format(root_org_id))
        sess.query(models.Organization).filter_by(
            root_organization_id=root_org_id).with_lockmode('update')

        where_expr = org_table.c.id == org.id
        sel = expr.select([org_table.c.left_sequence,
                           org_table.c.right_sequence])
        sel = sel.where(where_expr)
        row = conn.execute(sel).fetchone()
        lft, rgt = row
        width = rgt - lft + 1

        LOG.debug("Deleting organizations with left between {0} and {1} in "
                  "root org tree {2}.".format(lft, rgt, root_org_id))

        stmt = org_table.delete().where(
            org_table.c.left_sequence.between(lft, rgt)).where(
                org_table.c.root_organization_id == root_org_id)
        conn.execute(stmt)

        stmt = org_table.update().where(
            org_table.c.right_sequence > rgt).where(
                org_table.c.root_organization_id == root_org_id).values(
                    right_sequence=org_table.c.right_sequence - width)
        conn.execute(stmt)

        stmt = org_table.update().where(
            org_table.c.left_sequence > rgt).where(
                org_table.c.root_organization_id == root_org_id).values(
                    left_sequence=org_table.c.left_sequence - width)
        conn.execute(stmt)


def groups_get(ctx, spec, **kwargs):
    """
    Gets group models based on one or more search criteria.

    :param ctx: `procession.context.Context` object
    :param spec: `procession.api.SearchSpec` object that contains filters,
                 ordering, limits, etc
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use

    :raises `procession.exc.BadInput` if marker record not found
    :raises `ValueError` if search arguments didn't make sense
    :returns list of `procession.db.models.Group` objects
    """
    sess = kwargs.get('session', session.get_session())
    return _get_many(sess, models.Group, spec)


@if_slug_get_pk(models.Group)
def group_get_by_pk(ctx, group_id, **kwargs):
    """
    Convenience wrapper for common get by ID

    :param ctx: `procession.context.Context` object
    :param org_id: Group ID to look up
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use

    :raises `procession.exc.NotFound` if no org found matching
            search arguments
    :returns `procession.db.models.Group` object that was created
    """
    sess = kwargs.get('session', session.get_session())
    sargs = dict(id=group_id)
    return _get_one(sess, models.Group, **sargs)


def group_create(ctx, attrs, **kwargs):
    """
    Creates an group in the database. The session (either
    supplied or auto-created) is always committed upon successful
    creation.

    :param ctx: `procession.context.Context` object
    :param attrs: dict with information about the group to create
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use

    :raises `procession.exc.Duplicate` if org name already found
    :raises `ValueError` if validation of inputs fails
    :raises `TypeError` if unknown attribute is supplied
    :returns `procession.db.models.Group` object that was created
    """
    sess = kwargs.get('session', session.get_session())

    g = models.Group(**attrs)
    g.validate(attrs)

    root_org_id = attrs['root_organization_id']
    try:
        if _exists(sess, models.Group,
                   group_name=attrs['group_name'],
                   root_organization_id=attrs['root_organization_id']):
            msg = ("Organization with name {0} already exists within root "
                   "organization {1}.")
            msg = msg.format(attrs['group_name'],
                             attrs['root_organization_id'])
            raise exc.Duplicate(msg)
    except sa_exc.StatementError:
        msg = "Root organization ID {0} was badly formatted."
        msg = msg.format(root_org_id)
        raise exc.BadInput(msg)

    # Validate that the supplied root organization exists and is indeed
    # a root organization (has no parent)
    try:
        root = _get_one(sess, models.Organization, id=root_org_id)
        if root.parent_organization_id is not None:
            msg = "The specified organization {0} was not a root organization."
            msg = msg.format(root_org_id)
            raise exc.BadInput(msg)
    except exc.NotFound:
        msg = "The specified root organization {0} does not exist."
        msg = msg.format(root_org_id)
        raise exc.NotFound(msg)

    # Because of the unique constraint on (group_name, root_organization_id),
    # apparently SQLAlchemy does not automatically include the id column in
    # the list of attributes that it sets, so we must manually do that now.
    g.id = uuid.uuid4()

    g.set_slug()
    sess.add(g)
    sess.commit()
    msg = "Added new group {0} to root organization {1}."
    msg = msg.format(g.id, root_org_id)
    LOG.info(msg)
    return g


def group_delete(ctx, group_id, **kwargs):
    """
    Deletes a group from the database.

    :param ctx: `procession.context.Context` object
    :param group_id: ID of the group to delete
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use
        `commit`: Commit the session. Defaults to True. Set to False
                  to allow more efficient chaining of writes.

    :raises `procession.exc.NotFound` if group ID was not found.
    :raises `procession.exc.BadInput` if group ID was not a UUID.
    """
    sess = kwargs.get('session', session.get_session())
    commit = kwargs.get('commit', True)

    try:
        g = sess.query(models.Group).filter(
            models.Group.id == group_id).one()
        sess.delete(g)
        if commit:
            sess.commit()
        LOG.info("Deleted group with ID {0}".format(group_id))
    except sao_exc.NoResultFound:
        msg = "A group with ID {0} was not found.".format(group_id)
        raise exc.NotFound(msg)
    except sa_exc.StatementError:
        msg = "Group ID {0} was badly formatted.".format(group_id)
        raise exc.BadInput(msg)


def group_update(ctx, group_id, attrs, **kwargs):
    """
    Updates an group in the database.

    :param ctx: `procession.context.Context` object
    :param group_id: ID of the group to delete
    :param attrs: dict with information about the group to update
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use
        `commit`: Commit the session. Defaults to True. Set to False
                  to allow more efficient chaining of writes.

    :raises `procession.exc.NotFound` if group ID was not found.
    :raises `procession.exc.BadInput` if group ID was not a UUID, the
            root organization ID is missing or not a UUID, or the
            root organization ID is not a root org.
    :raises `procession.exc.Duplicate` if there was a change in group
            name and the results of that change resulted in a unique
            constraint violation. Note that this will only be raised
            if commit=True, since this is only caught if the session
            is committed during this method.
    """
    sess = kwargs.get('session', session.get_session())
    commit = kwargs.get('commit', True)

    try:
        g = sess.query(models.Group).filter(
            models.Group.id == group_id).one()
        g.validate(attrs)
        for name, value in attrs.items():
            if hasattr(g, name):
                setattr(g, name, value)
            else:
                msg = "Group model has no attribute {0}.".format(name)
                raise exc.BadInput(msg)

        # We need to ensure that the root organization is indeed
        # a root organization, and raise an error if it isn't
        if g.has_field_changed('root_organization_id'):
            root_org_id = attrs['root_organization_id']
            root = _get_one(sess, models.Organization, id=root_org_id)
            if root.parent_organization_id is not None:
                msg = "Organization {0} was not a root organization."
                msg = msg.format(root_org_id)
                raise exc.BadInput(msg)

        # Slug only changes if either root organization or group name
        # changes, and since the set_slug() method involves a call to
        # the DB to look up the root org's slug, we avoid that if we
        # know the slug won't change...
        changed = g.has_any_field_changed('root_organization_id',
                                          'group_name')
        if changed:
            g.set_slug()
        if commit:
            sess.commit()
        LOG.info("Updated group with ID {0}.".format(group_id))
        return g
    except ValueError:
        msg = ("Updated information for group was badly formatted. Was root "
               "organization not set properly?")
        raise exc.BadInput(msg)
    except sao_exc.NoResultFound:
        msg = "A group with ID {0} was not found.".format(group_id)
        raise exc.NotFound(msg)
    except sa_exc.IntegrityError:
        msg = "Group name or slug {0} was already in use.".format(
            attrs['group_name'])
        sess.rollback()
        raise exc.Duplicate(msg)
    except sa_exc.StatementError:
        msg = "Group ID {0} was badly formatted.".format(group_id)
        raise exc.BadInput(msg)


def group_users_get(ctx, group_id, **kwargs):
    """
    Gets user models that are members of the specified group.

    :param ctx: `procession.context.Context` object
    :param user_id: ID of the group to look up user membership for
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use

    :raises `procession.exc.BadInput` if group ID isn't a UUID
    """
    sess = kwargs.get('session', session.get_session())
    conn = sess.connection()

    user_table = models.User.__table__
    ugm_table = models.UserGroupMembership.__table__

    # Here's the SQL we are going for:
    #  SELECT u.* FROM users u
    #  INNER JOIN user_group_membership ugm
    #  ON ugm.user_id = u.id
    #  WHERE ugm.group_id = $group_id

    where_expr = ugm_table.c.group_id == group_id
    on_clause = ugm_table.c.user_id == user_table.c.id
    j = expr.join(ugm_table, user_table, on_clause)
    sel = expr.select([user_table]).select_from(j)
    sel = sel.where(where_expr)
    return conn.execute(sel).fetchall()


def users_get(ctx, spec, **kwargs):
    """
    Gets user models based on one or more search criteria.

    :param ctx: `procession.context.Context` object
    :param spec: `procession.api.SearchSpec` object that contains filters,
                 ordering, limits, etc
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use

    :raises `procession.exc.BadInput` if marker record not found
    :raises `ValueError` if search arguments didn't make sense
    :returns `procession.db.models.User` objects that matched search spec
    """
    sess = kwargs.get('session', session.get_session())
    return _get_many(sess, models.User, spec)


@if_slug_get_pk(models.User)
def user_get_by_pk(ctx, user_id, **kwargs):
    """
    Convenience wrapper for common get by ID

    :param ctx: `procession.context.Context` object
    :param user_id: User ID to look up
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use

    :raises `procession.exc.NotFound` if no user found matching
            search arguments
    :returns `procession.db.models.User` objects with specified ID
    """
    sess = kwargs.get('session', session.get_session())
    sargs = dict(id=user_id)
    return _get_one(sess, models.User, **sargs)


def user_create(ctx, attrs, **kwargs):
    """
    Creates a user in the database. The session (either supplied or
    auto-created) is always committed upon successful creation.

    :param ctx: `procession.context.Context` object
    :param attrs: dict with information about the user to create
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use

    :raises `procession.exc.Duplicate` if email already found
    :raises `ValueError` if validation of inputs fails
    :raises `TypeError` if unknown attribute is supplied
    :returns `procession.db.models.User` object that was created
    """
    sess = kwargs.get('session', session.get_session())

    u = models.User(**attrs)
    u.validate(attrs)
    u.set_slug()

    if _exists(sess, models.User, email=attrs['email']):
        msg = "User with email {0} already exists.".format(attrs['email'])
        raise exc.Duplicate(msg)

    sess.add(u)
    sess.commit()
    LOG.info("Added user {0}".format(u))
    return u


def user_delete(ctx, user_id, **kwargs):
    """
    Deletes a user from the database.

    :param ctx: `procession.context.Context` object
    :param user_id: ID of the user to delete
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use
        `commit`: Commit the session. Defaults to True. Set to False
                  to allow more efficient chaining of writes.

    :raises `procession.exc.NotFound` if user ID was not found.
    :raises `procession.exc.BadInput` if user ID was not a UUID.
    """
    sess = kwargs.get('session', session.get_session())
    commit = kwargs.get('commit', True)

    try:
        u = sess.query(models.User).filter(models.User.id == user_id).one()
        sess.delete(u)
        if commit:
            sess.commit()
        LOG.info("Deleted user with ID {0}.".format(user_id))
    except sao_exc.NoResultFound:
        msg = "A user with ID {0} was not found.".format(user_id)
        raise exc.NotFound(msg)
    except sa_exc.StatementError:
        msg = "User ID {0} was badly formatted.".format(user_id)
        raise exc.BadInput(msg)


def user_update(ctx, user_id, attrs, **kwargs):
    """
    Updates a user in the database.

    :param ctx: `procession.context.Context` object
    :param user_id: ID of the user to delete
    :param attrs: dict with information about the user to update
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use
        `commit`: Commit the session. Defaults to True. Set to False
                  to allow more efficient chaining of writes.

    :raises `procession.exc.NotFound` if user ID was not found.
    :raises `procession.exc.BadInput` if user ID was not a UUID.
    :raises `procession.exc.Duplicate` if there was a change in user
            name and the results of that change resulted in a unique
            constraint violation. Note that this will only be raised
            if commit=True, since this is only caught if the session
            is committed during this method.
    """
    sess = kwargs.get('session', session.get_session())
    commit = kwargs.get('commit', True)

    try:
        u = sess.query(models.User).filter(models.User.id == user_id).one()
        u.validate(attrs)
        for name, value in attrs.items():
            if hasattr(u, name):
                setattr(u, name, value)
            else:
                msg = "User model has no attribute {0}.".format(name)
                raise exc.BadInput(msg)
        u.set_slug()
        if commit:
            sess.commit()
        LOG.info("Updated user with ID {0}.".format(user_id))
        return u
    except sao_exc.NoResultFound:
        msg = "A user with ID {0} was not found.".format(user_id)
        raise exc.NotFound(msg)
    except sa_exc.IntegrityError:
        msg = "User name or slug {0} was already in use.".format(
            attrs['user_name'])
        sess.rollback()
        raise exc.Duplicate(msg)
    except sa_exc.StatementError:
        msg = "User ID {0} was badly formatted.".format(user_id)
        raise exc.BadInput(msg)


def user_groups_get(ctx, user_id, **kwargs):
    """
    Gets group models that the specified user is a member of.

    :param ctx: `procession.context.Context` object
    :param user_id: ID of the user to look up group membership for
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use

    :raises `procession.exc.BadInput` if user ID isn't a UUID
    """
    sess = kwargs.get('session', session.get_session())
    conn = sess.connection()

    group_table = models.Group.__table__
    ugm_table = models.UserGroupMembership.__table__

    # Here's the SQL we are going for:
    #  SELECT g.* FROM organization_groups g
    #  INNER JOIN user_group_membership ugm
    #  ON ugm.group_id = g.id
    #  WHERE ugm.user_id = $user_id

    where_expr = ugm_table.c.user_id == user_id
    on_clause = ugm_table.c.group_id == group_table.c.id
    j = expr.join(ugm_table, group_table, on_clause)
    sel = expr.select([group_table]).select_from(j)
    sel = sel.where(where_expr)
    return conn.execute(sel).fetchall()


def user_group_add(ctx, user_id, group_id, **kwargs):
    """
    Adds a user to a group.

    :param ctx: `procession.context.Context` object
    :param user_id: ID of the user to add to group
    :param group_id: ID of the group to add user to
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use
        `commit`: Commit the session. Defaults to False, to enable
                  more efficient chaining of writes.

    :raises `procession.exc.BadInput` if user ID or group ID
            isn't a UUID
    :raises `procession.exc.NotFound` if user ID or group ID
            was not found in the database.
    """
    sess = kwargs.get('session', session.get_session())
    commit = kwargs.get('commit', True)

    # This method does not raise an error if the group membership already
    # exists. We simply return the membership record.
    try:
        query = sess.query(models.UserGroupMembership)
        memberships = query.filter_by(
            group_id=group_id, user_id=user_id).all()
        if len(memberships) > 0:
            return memberships[0]
    except sa_exc.StatementError:
        msg = "User ID {0} or Group ID {1} was badly formatted."
        msg = msg.format(user_id, group_id)
        raise exc.BadInput(msg)

    if not _exists(sess, models.User, id=user_id):
        msg = "A user with ID {0} was not found.".format(user_id)
        raise exc.NotFound(msg)

    if not _exists(sess, models.Group, id=group_id):
        msg = "A group with ID {0} was not found.".format(group_id)
        raise exc.NotFound(msg)

    ugm = models.UserGroupMembership(user_id=user_id, group_id=group_id)
    sess.add(ugm)
    if commit:
        sess.commit()
    LOG.info("Added user {0} to group {1}.".format(user_id, group_id))
    return ugm


def user_group_remove(ctx, user_id, group_id, **kwargs):
    """
    Removes a user from a group.

    :param ctx: `procession.context.Context` object
    :param user_id: ID of the user to remove group membership
    :param group_id: ID of the group to delete user from
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use
        `commit`: Commit the session. Defaults to False, to enable
                  more efficient chaining of writes.

    :raises `procession.exc.NotFound` if user ID
            was not found in the database.
    :raises `procession.exc.BadInput` if user ID or group ID
            isn't a UUID
    """
    sess = kwargs.get('session', session.get_session())
    commit = kwargs.get('commit', True)

    if not _exists(sess, models.User, id=user_id):
        msg = "A user with ID {0} was not found.".format(user_id)
        raise exc.NotFound(msg)

    try:
        ugm = sess.query(models.UserGroupMembership).filter_by(
            user_id=user_id, group_id=group_id).one()
        sess.delete(ugm)
        if commit:
            sess.commit()
        LOG.info("Removed user {0} from group {1}.".format(user_id, group_id))
    except sao_exc.NoResultFound:
        # Do not raise an error if the group membership does
        # not already exist. We simply return None.
        return
    except sa_exc.StatementError:
        msg = "User ID {0} was badly formatted.".format(user_id)
        raise exc.BadInput(msg)


def user_keys_get(ctx, spec, **kwargs):
    """
    Gets user key models based on one or more search criteria.

    :param ctx: `procession.context.Context` object
    :param spec: `procession.api.SearchSpec` object that contains filters,
                 ordering, limits, etc
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use

    :raises `procession.exc.BadInput` if marker record not found
    :raises `ValueError` if search arguments didn't make sense
    """
    sess = kwargs.get('session', session.get_session())
    return _get_many(sess, models.UserPublicKey, spec)


def user_key_get_by_pk(ctx, user_id, fingerprint, **kwargs):
    """
    Convenience wrapper for common get by user ID and fingerprint

    :param ctx: `procession.context.Context` object
    :param user_id: User ID of key
    :param user_id: FIngerprint of key
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use

    :raises `procession.exc.NotFound` if no user found matching
            search arguments
    :returns `procession.db.models.UserPublicKey` object that was created
    """
    sess = kwargs.get('session', session.get_session())
    sargs = dict(user_id=user_id, fingerprint=fingerprint)
    return _get_one(sess, models.UserPublicKey, **sargs)


def user_key_create(ctx, user_id, attrs, **kwargs):
    """
    Creates a user key in the database.

    :param ctx: `procession.context.Context` object
    :param user_id: ID of the user to add the key to
    :param attrs: dict with information about the user to create
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use
        `commit`: Commit the session. Defaults to False, to enable
                  more efficient chaining of writes.

    :raises `procession.exc.Duplicate` if email already found
    :raises `ValueError` if validation of inputs fails
    :returns `procession.db.models.UserPublicKey` object that was created
    """
    sess = kwargs.get('session', session.get_session())
    commit = kwargs.get('commit', False)

    if not _exists(sess, models.User, id=user_id):
        msg = "A user with ID {0} was not found.".format(user_id)
        raise exc.NotFound(msg)

    k = models.UserPublicKey(**attrs)
    k.user_id = user_id
    k.validate(attrs)

    if _exists(sess, models.UserPublicKey, fingerprint=attrs['fingerprint']):
        msg = "Key with fingerprint {0} already exists."
        msg = msg.format(attrs['fingerprint'])
        raise exc.Duplicate(msg)

    sess.add(k)
    if commit:
        sess.commit()
    LOG.info("Added key with fingerprint {0} for user with ID {1}.".format(
        k.fingerprint, user_id))
    return k


def user_key_delete(ctx, user_id, fingerprint, **kwargs):
    """
    Deletes a user key from the database.

    :param ctx: `procession.context.Context` object
    :param user_id: ID of the user to delete the key from
    :param fingerprint: Fingerprint of the key to delete
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use

    :raises `procession.exc.NotFound` if user ID or key with fingerprint
            was not found.
    :raises `procession.exc.BadInput` if user ID was not a UUID or key
            fingerprint was not a fingerprint.
    """
    sess = kwargs.get('session', session.get_session())

    try:
        k = sess.query(models.UserPublicKey).filter(
            models.User.id == user_id,
            models.UserPublicKey.fingerprint == fingerprint).one()
        sess.delete(k)
        LOG.info("Deleted user public key with fingerprint {0} for user with "
                 "ID {1}.".format(fingerprint, user_id))
    except sao_exc.NoResultFound:
        msg = ("A user with ID {0} or a key with fingerprint {1} was not "
               "found.").format(user_id, fingerprint)
        raise exc.NotFound(msg)
    except sa_exc.StatementError:
        msg = "Something was badly formatted.".format(user_id)
        raise exc.BadInput(msg)


def domains_get(ctx, spec, **kwargs):
    """
    Gets domain models based on one or more search criteria.

    :param ctx: `procession.context.Context` object
    :param spec: `procession.api.SearchSpec` object that contains filters,
                 ordering, limits, etc
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use

    :raises `procession.exc.BadInput` if marker record not found
    :raises `ValueError` if search arguments didn't make sense
    :returns `procession.db.models.Domain` objects that matched search spec
    """
    sess = kwargs.get('session', session.get_session())
    return _get_many(sess, models.Domain, spec)


@if_slug_get_pk(models.Domain)
def domain_repos_get(ctx, domain_id, spec, **kwargs):
    """
    A helper method that returns the repositories for a given domain.

    :param ctx: `procession.context.Context` object
    :param domain_id: ID or slug of the domain.
    :param spec: `procession.api.SearchSpec` object that contains filters,
                 ordering, limits, etc
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use

    :raises `procession.exc.BadInput` if marker record not found.
    :raises `procession.exc.NotFound` if domain not found.
    :raises `ValueError` if search arguments didn't make sense
    :returns `procession.db.models.Repository` objects that matched search
             spec
    """
    sess = kwargs.get('session', session.get_session())
    spec.filters['domain_id'] = domain_id
    return _get_many(sess, models.Repository, spec)


@if_slug_get_pk(models.Domain)
def domain_repo_get_by_name(ctx, domain_id, repo_name, **kwargs):
    """
    A helper method that returns a single repository in a given domain
    that matches on a repository name or ID.

    :param ctx: `procession.context.Context` object
    :param domain_id: ID or slug of the domain.
    :param repo_name: Name or ID of repository.
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use

    :raises `procession.exc.BadInput` if marker record not found.
    :raises `procession.exc.NotFound` if domain or repository not found.
    :raises `ValueError` if search arguments didn't make sense
    :returns `procession.db.models.Repository` object.
    """
    sess = kwargs.get('session', session.get_session())
    filters = dict(domain_id=domain_id)
    if helpers.is_like_uuid(repo_name):
        filters['id'] = repo_name
    else:
        filters['name'] = repo_name

    try:
        return _get_one(sess, models.Repository, **filters)
    except exc.NotFound:
        msg = "Repo {0} in domain {1} does not exist."
        msg = msg.format(repo_name, domain_id)
        raise exc.NotFound(msg)


@if_slug_get_pk(models.Domain)
def domain_get_by_pk(ctx, domain_id, **kwargs):
    """
    Convenience wrapper for common get by ID

    :param ctx: `procession.context.Context` object
    :param domain_id: Domain ID to look up
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use

    :raises `procession.exc.NotFound` if no domain found matching
            search arguments
    :returns `procession.db.models.Domain` objects with specified ID
    """
    sess = kwargs.get('session', session.get_session())
    sargs = dict(id=domain_id)
    return _get_one(sess, models.Domain, **sargs)


def domain_create(ctx, attrs, **kwargs):
    """
    Creates a domain in the database. The session (either supplied or
    auto-created) is always committed upon successful creation.

    :param ctx: `procession.context.Context` object
    :param attrs: dict with information about the domain to create
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use

    :raises `procession.exc.Duplicate` if email already found
    :raises `ValueError` if validation of inputs fails
    :raises `TypeError` if unknown attribute is supplied
    :raises `procession.exc.NotFound` if no user with owner_id
    :returns `procession.db.models.Domain` object that was created
    """
    sess = kwargs.get('session', session.get_session())

    d = models.Domain(**attrs)
    d.validate(attrs)
    d.set_slug()

    if not _exists(sess, models.User, id=attrs['owner_id']):
        msg = "A user with ID {0} does not exist.".format(attrs['owner_id'])
        raise exc.NotFound(msg)

    if _exists(sess, models.Domain, name=attrs['name']):
        msg = "Domain with name {0} already exists.".format(attrs['name'])
        raise exc.Duplicate(msg)

    sess.add(d)
    sess.commit()
    LOG.info("Added domain {0}".format(d))
    return d


def domain_delete(ctx, domain_id, **kwargs):
    """
    Deletes a domain from the database.

    :param ctx: `procession.context.Context` object
    :param domain_id: ID of the domain to delete
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use
        `commit`: Commit the session. Defaults to True. Set to False
                  to allow more efficient chaining of writes.

    :raises `procession.exc.NotFound` if domain ID was not found.
    :raises `procession.exc.BadInput` if domain ID was not a UUID.
    """
    sess = kwargs.get('session', session.get_session())
    commit = kwargs.get('commit', True)

    try:
        d = sess.query(models.Domain).filter(
            models.Domain.id == domain_id).one()
        sess.delete(d)
        if commit:
            sess.commit()
        LOG.info("Deleted domain with ID {0}.".format(domain_id))
    except sao_exc.NoResultFound:
        msg = "A domain with ID {0} was not found.".format(domain_id)
        raise exc.NotFound(msg)
    except sa_exc.StatementError:
        msg = "Domain ID {0} was badly formatted.".format(domain_id)
        raise exc.BadInput(msg)


def domain_update(ctx, domain_id, attrs, **kwargs):
    """
    Updates a domain in the database.

    :param ctx: `procession.context.Context` object
    :param domain_id: ID of the domain to delete
    :param attrs: dict with information about the domain to update
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use
        `commit`: Commit the session. Defaults to True. Set to False
                  to allow more efficient chaining of writes.

    :raises `procession.exc.NotFound` if domain ID was not found.
    :raises `procession.exc.BadInput` if domain ID was not a UUID.
    :raises `procession.exc.Duplicate` if there was a change in domain
            name and the results of that change resulted in a unique
            constraint violation. Note that this will only be raised
            if commit=True, since this is only caught if the session
            is committed during this method.
    """
    sess = kwargs.get('session', session.get_session())
    commit = kwargs.get('commit', True)

    try:
        d = sess.query(models.Domain).filter(
            models.Domain.id == domain_id).one()
        d.validate(attrs)
        for name, value in attrs.items():
            if hasattr(d, name):
                setattr(d, name, value)
            else:
                msg = "Domain model has no attribute {0}.".format(name)
                raise exc.BadInput(msg)

        # We need to ensure that if the owner of the domain has changed,
        # that we check the new owner exists, and trigger any necessary
        # access control changes that are necessary.
        if d.has_field_changed('owner_id'):
            # We need to grab orig owner here, because for some reason (
            # perhaps because the session is used in the _exists() call?)
            # if we do it after the _exists() check, the orig_owner is always
            # None.
            orig_owner = str(d.get_earliest_value('owner_id'))
            owner_id = attrs['owner_id']
            if not helpers.is_like_uuid(owner_id):
                sess.rollback()
                msg = "Owner ID {0} is badly formatted.".format(owner_id)
                raise exc.BadInput(msg)
            if not _exists(sess, models.User, id=owner_id):
                sess.rollback()
                msg = "A user with ID {0} does not exist.".format(owner_id)
                raise exc.NotFound(msg)

            msg = ("Transferring ownership of domain {0} from "
                   "user {1} to user {2}.")
            msg = msg.format(domain_id, orig_owner, owner_id)
            LOG.info(msg)
            #TODO(jaypipes): Trigger ACL changes

        d.set_slug()
        if commit:
            sess.commit()
        LOG.info("Updated domain with ID {0}.".format(domain_id))
        return d
    except ValueError:
        msg = "Could not update domain {0}. A required attribute was missing."
        msg = msg.format(domain_id)
        raise exc.BadInput(msg)
    except sao_exc.NoResultFound:
        msg = "A domain with ID {0} was not found.".format(domain_id)
        raise exc.NotFound(msg)
    except sa_exc.IntegrityError:
        msg = "Domain name or slug {0} was already in use.".format(
            attrs['name'])
        sess.rollback()
        raise exc.Duplicate(msg)
    except sa_exc.StatementError:
        msg = "Domain ID {0} was badly formatted.".format(domain_id)
        raise exc.BadInput(msg)


def repos_get(ctx, spec, **kwargs):
    """
    Gets repo models based on one or more search criteria.

    :param ctx: `procession.context.Context` object
    :param spec: `procession.api.SearchSpec` object that contains filters,
                 ordering, limits, etc
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use

    :raises `procession.exc.BadInput` if marker record not found
    :raises `ValueError` if search arguments didn't make sense
    :returns `procession.db.models.Repository` objects that matched search spec
    """
    sess = kwargs.get('session', session.get_session())
    return _get_many(sess, models.Repository, spec)


@if_slug_get_pk(models.Repository)
def repo_get_by_pk(ctx, repo_id, **kwargs):
    """
    Convenience wrapper for common get by ID

    :param ctx: `procession.context.Context` object
    :param repo_id: Repository ID to look up
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use

    :raises `procession.exc.NotFound` if no repo found matching
            search arguments
    :returns `procession.db.models.Repository` objects with specified ID
    """
    sess = kwargs.get('session', session.get_session())
    sargs = dict(id=repo_id)
    return _get_one(sess, models.Repository, **sargs)


def repo_create(ctx, attrs, **kwargs):
    """
    Creates a repo in the database. The session (either supplied or
    auto-created) is always committed upon successful creation.

    :param ctx: `procession.context.Context` object
    :param attrs: dict with information about the repo to create
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use

    :raises `procession.exc.Duplicate` if email already found
    :raises `ValueError` if validation of inputs fails
    :raises `TypeError` if unknown attribute is supplied
    :raises `procession.exc.NotFound` if no user with owner_id
    :returns `procession.db.models.Repository` object that was created
    """
    sess = kwargs.get('session', session.get_session())

    r = models.Repository(**attrs)
    r.validate(attrs)

    if not _exists(sess, models.User, id=attrs['owner_id']):
        msg = "A user with ID {0} does not exist.".format(attrs['owner_id'])
        raise exc.NotFound(msg)

    if not _exists(sess, models.Domain, id=attrs['domain_id']):
        msg = "A domain with ID {0} does not exist."
        msg = msg.format(attrs['domain_id'])
        raise exc.NotFound(msg)

    if _exists(sess, models.Repository, domain_id=attrs['domain_id'],
               name=attrs['name']):
        msg = "Repository with name {0} already exists in domain {1}."
        msg = msg.format(attrs['name'], attrs['domain_id'])
        raise exc.Duplicate(msg)

    sess.add(r)
    sess.commit()
    LOG.info("Added repo {0}".format(r))
    return r


def repo_delete(ctx, repo_id, **kwargs):
    """
    Deletes a repo from the database.

    :param ctx: `procession.context.Context` object
    :param repo_id: ID of the repo to delete
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use
        `commit`: Commit the session. Defaults to True. Set to False
                  to allow more efficient chaining of writes.

    :raises `procession.exc.NotFound` if repo ID was not found.
    :raises `procession.exc.BadInput` if repo ID was not a UUID.
    """
    sess = kwargs.get('session', session.get_session())
    commit = kwargs.get('commit', True)

    try:
        r = sess.query(models.Repository).filter(
            models.Repository.id == repo_id).one()
        sess.delete(r)
        if commit:
            sess.commit()
        LOG.info("Deleted repo with ID {0}.".format(repo_id))
    except sao_exc.NoResultFound:
        msg = "A repo with ID {0} was not found.".format(repo_id)
        raise exc.NotFound(msg)
    except sa_exc.StatementError:
        msg = "Repository ID {0} was badly formatted.".format(repo_id)
        raise exc.BadInput(msg)


def repo_update(ctx, repo_id, attrs, **kwargs):
    """
    Updates a repo in the database.

    :param ctx: `procession.context.Context` object
    :param repo_id: ID of the repo to delete
    :param attrs: dict with information about the repo to update
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use
        `commit`: Commit the session. Defaults to True. Set to False
                  to allow more efficient chaining of writes.

    :raises `procession.exc.NotFound` if repo ID was not found.
    :raises `procession.exc.BadInput` if repo ID was not a UUID.
    :raises `procession.exc.Duplicate` if there was a change in repo
            name and the results of that change resulted in a unique
            constraint violation. Note that this will only be raised
            if commit=True, since this is only caught if the session
            is committed during this method.
    """
    sess = kwargs.get('session', session.get_session())
    commit = kwargs.get('commit', True)

    try:
        r = sess.query(models.Repository).filter(
            models.Repository.id == repo_id).one()
        r.validate(attrs)
        for name, value in attrs.items():
            if hasattr(r, name):
                setattr(r, name, value)
            else:
                msg = "Repository model has no attribute {0}.".format(name)
                raise exc.BadInput(msg)

        if r.has_field_changed('domain_id'):
            domain_id = attrs['domain_id']
            if not helpers.is_like_uuid(domain_id):
                sess.rollback()
                msg = "Domain ID {0} is badly formatted.".format(domain_id)
                raise exc.BadInput(msg)
            if not _exists(sess, models.Domain, id=domain_id):
                sess.rollback()
                msg = "A domain with ID {0} does not exist.".format(domain_id)
                raise exc.NotFound(msg)

        # We need to ensure that if the owner of the repo has changed,
        # that we check the new owner exists, and trigger any necessary
        # access control changes that are necessary.
        if r.has_field_changed('owner_id'):
            # We need to grab orig owner here, because for some reason (
            # perhaps because the session is used in the _exists() call?)
            # if we do it after the _exists() check, the orig_owner is always
            # None.
            orig_owner = str(r.get_earliest_value('owner_id'))
            owner_id = attrs['owner_id']
            if not helpers.is_like_uuid(owner_id):
                sess.rollback()
                msg = "Owner ID {0} is badly formatted.".format(owner_id)
                raise exc.BadInput(msg)
            if not _exists(sess, models.User, id=owner_id):
                sess.rollback()
                msg = "A user with ID {0} does not exist.".format(owner_id)
                raise exc.NotFound(msg)

            msg = ("Transferring ownership of repo {0} from "
                   "user {1} to user {2}.")
            msg = msg.format(repo_id, orig_owner, owner_id)
            LOG.info(msg)
            #TODO(jaypipes): Trigger ACL changes

        if commit:
            sess.commit()
        LOG.info("Updated repo with ID {0}.".format(repo_id))
        return r
    except ValueError:
        msg = "Could not update repo {0}. A required attribute was missing."
        msg = msg.format(repo_id)
        raise exc.BadInput(msg)
    except sao_exc.NoResultFound:
        msg = "A repo with ID {0} was not found.".format(repo_id)
        raise exc.NotFound(msg)
    except sa_exc.IntegrityError:
        msg = "Repository name or slug {0} was already in use.".format(
            attrs['name'])
        sess.rollback()
        raise exc.Duplicate(msg)
    except sa_exc.StatementError:
        msg = "Repository ID {0} was badly formatted.".format(repo_id)
        raise exc.BadInput(msg)


def changesets_get(ctx, spec, **kwargs):
    """
    Gets changeset models based on one or more search criteria.

    :param ctx: `procession.context.Context` object
    :param spec: `procession.api.SearchSpec` object that contains filters,
                 ordering, limits, etc
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use

    :raises `procession.exc.BadInput` if marker record not found
    :raises `ValueError` if search arguments didn't make sense
    :returns `procession.db.models.Changeset` objects that matched search spec
    """
    sess = kwargs.get('session', session.get_session())
    return _get_many(sess, models.Changeset, spec)


def changeset_get_by_pk(ctx, changeset_id, **kwargs):
    """
    Convenience wrapper for common get by ID

    :param ctx: `procession.context.Context` object
    :param changeset_id: Changeset ID to look up
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use

    :raises `procession.exc.NotFound` if no changeset found matching
            search arguments
    :returns `procession.db.models.Changeset` objects with specified ID
    """
    sess = kwargs.get('session', session.get_session())
    sargs = dict(id=changeset_id)
    return _get_one(sess, models.Changeset, **sargs)


def changeset_create(ctx, attrs, **kwargs):
    """
    Creates a changeset in the database. The session (either supplied or
    auto-created) is always committed upon successful creation.

    :param ctx: `procession.context.Context` object
    :param attrs: dict with information about the changeset to create
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use

    :raises `procession.exc.Duplicate` if email already found
    :raises `ValueError` if validation of inputs fails
    :raises `TypeError` if unknown attribute is supplied
    :raises `procession.exc.NotFound` if no user with owner_id
    :returns `procession.db.models.Changeset` object that was created
    """
    sess = kwargs.get('session', session.get_session())

    c = models.Changeset(**attrs)
    c.validate(attrs)

    if not _exists(sess, models.User, id=attrs['uploaded_by']):
        msg = "Uploading user with ID {0} does not exist."
        msg = msg.format(attrs['uploaded_by'])
        raise exc.NotFound(msg)

    if not _exists(sess, models.Repository, id=attrs['target_repo_id']):
        msg = "A repo with ID {0} does not exist."
        msg = msg.format(attrs['target_repo_id'])
        raise exc.NotFound(msg)

    #TODO(jaypipes): Will need to call out to git here to verify
    #                the target_branch exists.

    #TODO(jaypipes): Allow DRAFT state as well once enum types are done
    c.state = models.Changeset.STATE_ACTIVE
    sess.add(c)
    sess.commit()
    LOG.info("Added changeset {0}".format(c))
    return c


def changeset_delete(ctx, changeset_id, **kwargs):
    """
    Deletes a changeset from the database.

    :param ctx: `procession.context.Context` object
    :param changeset_id: ID of the changeset to delete
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use
        `commit`: Commit the session. Defaults to True. Set to False
                  to allow more efficient chaining of writes.

    :raises `procession.exc.NotFound` if changeset ID was not found.
    :raises `procession.exc.BadInput` if changeset ID was not a UUID.
    """
    sess = kwargs.get('session', session.get_session())
    commit = kwargs.get('commit', True)

    try:
        c = sess.query(models.Changeset).filter(
            models.Changeset.id == changeset_id).one()
        sess.delete(c)
        if commit:
            sess.commit()
        LOG.info("Deleted changeset with ID {0}.".format(changeset_id))
    except sao_exc.NoResultFound:
        msg = "A changeset with ID {0} was not found.".format(changeset_id)
        raise exc.NotFound(msg)
    except sa_exc.StatementError:
        msg = "Changeset ID {0} was badly formatted.".format(changeset_id)
        raise exc.BadInput(msg)


def _get_many(sess, model, spec):
    """
    Returns an iterable of model objects give the supplied model and search
    spec.

    :param sess: `sqlalchemy.orm.Session` object
    :param model: the model to query on (either fully-qualified string
                  or a model class object
    :param spec: `procession.api.SearchSpec` object that contains filters,
                 ordering, limits, etc

    :raises `procession.exc.BadInput` if marker record does not exist.
    """
    query = sess.query(model)
    if spec.filters:
        query = query.filter_by(**spec.filters)

    order_by = spec.get_order_by()
    if not order_by:
        order_by = model.get_default_order_by()

    # Here, we handle the pagination filters. The marker field of the
    # spec is the primary key of the last record on the "previous" page
    # of search results that was returned. If necessary, we grab the
    # marker record from the database and use the marker record's field
    # values that match the sort order columns to build up a set of filters.
    if spec.marker is not None:
        query = _paginate_query(sess, query, model, spec.marker, order_by)
    else:
        query = query.order_by(*order_by)

    query = query.limit(spec.limit)

    return query.all()


def _get_one(sess, model, **sargs):
    """
    Returns a single model object if the model exists, otherwise raises
    `procession.exc.NotFound`.

    :param sess: `sqlalchemy.orm.Session` object
    :param model: the model to query on (either fully-qualified string
                  or a model class object
    :param sargs: dict with attr/value pairs to use as search
                  arguments

    :raises `procession.exc.NotFound` if no object found matching
            search arguments
    """
    try:
        return sess.query(model).filter_by(**sargs).one()
    except sao_exc.NoResultFound:
        raise exc.NotFound()


def _exists(sess, model, **by):
    """
    Returns True if the model exists, False otherwise.

    :param sess: `sqlalchemy.orm.Session` object
    :param model: the model to query on (either fully-qualified string
                  or a model class object
    :param by: Keyword arguments. The lookup is performed on the columns
               specified in the kwargs.
    """
    try:
        col = getattr(model, by.keys()[0])
        sess.query(col).filter_by(**by).limit(1).one()
        return True
    except sao_exc.NoResultFound:
        return False


def _ensure_unique_sort(model, order_by):
    """
    Ensures that the supplied set of sort specs includes at least one unique
    column, and returns a list of "$FIELD $DIR" strings to be used in
    ordering.

    :param model: the model to query on (either fully-qualified string
                  or a model class object
    :param spec: `procession.api.SearchSpec` object that contains filters,
                 ordering, limits, etc
    """
    # Ensure that we have at least one column in the sort fields that
    # is unique. It is not possible to ensure lexicographic ordering
    # without at least one unique column in the ordering.
    need_unique_sort = True
    for sort_spec in order_by:
        sort_field_name, sort_dir = sort_spec.split(' ')
        sort_field = getattr(model, sort_field_name)
        if sort_field.unique:
            need_unique_sort = False
            break
    if need_unique_sort:
        # Add the model's primary key columns to the ordering. The
        # sort direction doesn't matter, as this is just used to
        # ensure ordering consistency, so we just use ascending sort.
        for pk_col in model.get_primary_key_columns():
            order_by.append("{0} asc".format(pk_col.name))
    return order_by


def _paginate_query(sess, query, model, marker, order_by):
    """
    Helper method that adds search conditions to the supplied
    query that provide the winnowing function for marker/limit
    pagination. Returns the adapted query object.

    :param sess: `sqlalchemy.orm.Session` object
    :param query: `sqlalchemy.Query` object to adapt with filters
    :param model: the model to query on (either fully-qualified string
                  or a model class object
    :param marker: The primary key of the marker record
    :param order_by: List of sort specs in the form of "$FIELD $DIR"
    """
    order_by = _ensure_unique_sort(model, order_by)

    pk_cols = model.get_primary_key_columns()
    if len(pk_cols) == 1:
        try:
            marker_record = sess.query(model).filter(
                pk_cols[0] == marker).one()
        except sao_exc.NoResultFound:
            msg = "Marker record not found."
            raise exc.BadInput(msg)
        except sa_exc.StatementError:
            msg = "Invalid marker record."
            raise exc.BadInput(msg)
    else:
        # TODO(jaypipes): Handle multi-PK models
        pass

    # Here we add the filters that enable pagination. For each field
    # that is used for sorting, we add a filter to the query that winnows
    # the data set to records not matching the marker record's values
    # for those sort fields. The query that will be produced for a search
    # that is sorted on three columns in ascending direction looks like
    # the following:
    #
    #  SELECT .. FROM {model_table}
    #  WHERE {search filters}
    #  AND (
    #   {sort field 1} > {marker sort field 1 value}
    #   OR (
    #    {sort_field 2} > {marker sort field 2 value}
    #    AND {sort field 1} = {marker sort field 1 value}
    #   )
    #   OR (
    #    {sort_field 3} > {marker sort field 3 value}
    #    AND {sort_field 2} = {marker sort field 2 value}
    #    AND {sort field 1} = {marker sort field 1 value}
    #   )
    #  )
    #  ORDER BY {sort fields}
    #
    num_sorts = len(order_by)
    sort_conds = []
    for cur_sort in xrange(num_sorts):
        sort_field_name, sort_dir = order_by[cur_sort].split(' ')
        sort_field = getattr(model, sort_field_name)
        marker_value = getattr(marker_record, sort_field_name)
        conds = []
        if sort_dir.lower() == 'asc':
            conds.append(sort_field > marker_value)
        else:
            conds.append(sort_field < marker_value)
        # Add equality conditions for each other sort field
        for prev_sort in xrange(cur_sort):
            sort_field_name, sort_dir = order_by[prev_sort].split(' ')
            sort_field = getattr(model, sort_field_name)
            marker_value = getattr(marker_record, sort_field_name)
            conds.append(sort_field == marker_value)
        sort_conds.append(sqlalchemy.and_(*conds))
    query = query.filter(sqlalchemy.or_(*sort_conds))
    query = query.order_by(*order_by)
    return query
