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

"""
Defines the internal API for procession's database. This is an internal
API and may change at any time. If you are looking for a stable API to
community with Procession, use the public REST API or alternately, use
the python-processionclient's public Python API.
"""

import functools
import logging

from oslo.config import cfg
import sqlalchemy
from sqlalchemy import exc as sa_exc
from sqlalchemy.orm import exc as sao_exc

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
                    return f(ctx, real_pk_value.id, **kwargs)
                except sao_exc.NoResultFound:
                    msg = ("An object with slug {0} "
                           "was not found.").format(pk_or_slug)
                    raise exc.NotFound(msg)
            return f(*args, **kwargs)
        return wrapper
    return decorator


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
    :returns `procession.db.models.User` object that was created
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
    :returns `procession.db.models.User` object that was created
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

    if _exists(sess, models.User, email=attrs['email']):
        msg = "User with email {0} already exists".format(attrs['email'])
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

    :raises `procession.exc.NotFound` if user ID was not found.
    :raises `procession.exc.BadInput` if user ID was not a UUID.
    """
    sess = kwargs.get('session', session.get_session())

    try:
        u = sess.query(models.User).filter(models.User.id == user_id).one()
        sess.delete(u)
        LOG.info("Deleted user with ID {0}".format(u))
    except sao_exc.NoResultFound:
        msg = "A user with ID {0} was not found.".format(user_id)
        raise exc.NotFound(msg)
    except sa_exc.StatementError as e:
        msg = "User ID {0} was badly formatted.".format(user_id)
        LOG.debug("{0}: Details: {1}".format(msg, e))
        raise exc.BadInput(msg)


def user_update(ctx, user_id, attrs, **kwargs):
    """
    Updates a user in the database.

    :param ctx: `procession.context.Context` object
    :param user_id: ID of the user to delete
    :param attrs: dict with information about the user to update
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use
        `commit`: Commit the session. Defaults to False, to enable
                  more efficient chaining of writes.

    :raises `procession.exc.NotFound` if user ID was not found.
    :raises `procession.exc.BadInput` if user ID was not a UUID.
    """
    sess = kwargs.get('session', session.get_session())
    commit = kwargs.get('commit', False)

    try:
        u = sess.query(models.User).filter(models.User.id == user_id).one()
        u.validate(attrs)
        for name, value in attrs.items():
            if hasattr(u, name):
                setattr(u, name, value)
            else:
                msg = "User model has no attribute {0}.".format(name)
                LOG.debug(msg)
                raise exc.BadInput(msg)
        LOG.info("Updated user with ID {0}".format(u))
        if commit:
            sess.commit()
        return u
    except sao_exc.NoResultFound:
        msg = "A user with ID {0} was not found.".format(user_id)
        raise exc.NotFound(msg)
    except sa_exc.StatementError as e:
        msg = "User ID {0} was badly formatted.".format(user_id)
        LOG.debug("{0}: Details: {1}".format(msg, e))
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
        msg = "Key with fingerprint {0} already exists"
        msg = msg.format(attrs['fingerprint'])
        raise exc.Duplicate(msg)

    sess.add(k)
    if commit:
        sess.commit()
    LOG.info("Added key with fingerprint {0} for user with ID {1}".format(
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
                 "ID {1}".format(fingerprint, user_id))
    except sao_exc.NoResultFound:
        msg = ("A user with ID {0} or a key with fingerprint {1} was not "
               "found.").format(user_id, fingerprint)
        raise exc.NotFound(msg)
    except sa_exc.StatementError as e:
        msg = "Something was badly formatted.".format(user_id)
        LOG.debug("{0}: Details: {1}".format(msg, e))
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
    return sess.query(model).filter_by(**by).count() != 0


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
