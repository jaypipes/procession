# -*- mode: python -*-
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

import logging

from oslo.config import cfg
from sqlalchemy import exc as sa_exc
from sqlalchemy.orm import exc as sao_exc

from procession import exc
from procession.db import models
from procession.db import session

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def users_get(ctx, spec, **kwargs):
    """
    Gets user models based on one or more search criteria.

    :param ctx: `procession.context.Context` object
    :param spec: `procession.api.SearchSpec` object that contains filters,
                 ordering, limits, etc
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use

    :raises `procession.exc.NotFound` if no user found matching
            search arguments
    :raises `ValueError` if search arguments didn't make sense
    :returns `procession.db.models.User` object that was created
    """
    sess = kwargs.get('session', session.get_session())
    return _get_many(sess, models.User, spec)


def user_get_by_id(ctx, user_id, **kwargs):
    """
    Convenience wrapper for common get by ID routine

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
    Creates a user in the database.

    :param ctx: `procession.context.Context` object
    :param attrs: dict with information about the user to create
    :param kwargs: optional keywords arguments to the function:

        `session`: A session object to use

    :raises `procession.exc.Duplicate` if email already found
    :raises `ValueError` if validation of inputs fails
    :returns `procession.db.models.User` object that was created
    """
    sess = kwargs.get('session', session.get_session())

    u = models.User(**attrs)
    u.validate(attrs)

    if _exists(sess, models.User, email=attrs['email']):
        msg = "User with email {0} already exists".format(attrs['email'])
        raise exc.Duplicate(msg)

    sess.add(u)
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

    :raises `procession.exc.NotFound` if user ID was not found.
    :raises `procession.exc.BadInput` if user ID was not a UUID.
    """
    sess = kwargs.get('session', session.get_session())

    try:
        u = sess.query(models.User).filter(models.User.id == user_id).one()
        u.validate(attrs)
        for name, value in attrs.items():
            if hasattr(u, name):
                setattr(u, name, value)
            else:
                LOG.warning("User model has no attribute {0}".format(name))
        return u
        LOG.info("Updated user with ID {0}".format(u))
    except sao_exc.NoResultFound:
        msg = "A user with ID {0} was not found.".format(user_id)
        raise exc.NotFound(msg)
    except sa_exc.StatementError as e:
        msg = "User ID {0} was badly formatted.".format(user_id)
        LOG.debug("{0}: Details: {1}".format(msg, e))
        raise exc.BadInput(msg)


def _get_many(sess, model, spec):
    """
    Returns an iterable of model objects give the supplied model and search
    spec.

    :param sess: `sqlalchemy.orm.Session` object
    :parm model: the model to query on (either fully-qualified string
                 or a model class object
    :param spec: `procession.api.SearchSpec` object that contains filters,
                 ordering, limits, etc
    """
    query = sess.query(model)
    if spec.filters:
        query.filter_by(**spec.filters)
    if spec.sort_by:
        query.order_by(*spec.get_order_by())
    else:
        query.order_by(*model.default_order_by())

    return query.all()


def _get_one(sess, model, **sargs):
    """
    Returns a single model object if the model exists, otherwise raises
    `procession.exc.NotFound`.

    :param sess: `sqlalchemy.orm.Session` object
    :parm model: the model to query on (either fully-qualified string
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
    :parm model: the model to query on (either fully-qualified string
                 or a model class object
    :param by: Keyword arguments. The lookup is performed on the columns
               specified in the kwargs.
    """
    return sess.query(model).filter_by(**by).count() != 0
