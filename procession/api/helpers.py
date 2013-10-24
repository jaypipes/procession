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

import json
import yaml

from falcon import exceptions as fexc

from procession.db import models

ALLOWED_MIME_TYPES = [
    'application/json',
    'application/yaml'
]


def serialize(req, subject):
    """
    Returns a serialized string representing the supplied subject. We do some
    introspection of the supplied subject to convert the subject to a dict or
    list of dicts if the subject is not already a dict or list of dicts.

    :param subject: The thing or things to serialize
    :param request: `falcon.request.Request` object that is used to determine
                    how to serialize the data

    :raises `falcon.exceptions.HTTPNotAcceptable` if the request does not
            accept one of the acceptable serialization MIME types.
    """
    if isinstance(subject, list):
        if len(subject) > 0 and isinstance(subject[0], models.ModelBase):
            subject = [m.to_dict() for m in subject]
    elif isinstance(subject, models.ModelBase):
        subject = subject.to_dict()

    prefers = req.client_prefers(ALLOWED_MIME_TYPES)
    if prefers is None:
        msg = ("Procession's API works with JSON or YAML. "
               "{0} is not supported.".format(req.accept))
        raise fexc.HTTPNotAcceptable(msg)

    return {
        'application/json': serialize_json,
        'application/yaml': serialize_yaml
    }[prefers](subject)


def serialize_json(subject):
    """
    Returns a JSON-serialized string representing the supplied dict or
    list of dicts.

    :param subject: dict or list of dicts to serialize
    """
    return json.dumps(subject, 'utf-8')


def serialize_yaml(subject):
    """
    Returns a JSON-serialized string representing the supplied dict or
    list of dicts.

    :param subject: dict or list of dicts to serialize
    """
    return yaml.dump(subject)


def deserialize(req):
    """
    Returns a dict or list of dicts by reading the supplied request body
    and attempting to deserialize the contents after looking at the request's
    Content-Type header.

    :param request: `falcon.request.Request` object whose body is deserialized

    :raises `falcon.exceptions.HTTPNotAcceptable` if the request content type
            is not an accepted MIME types.
    :raises `ValueError` if serialization fails.
    """

    content_type = req.content_type.lower()
    if not content_type in ALLOWED_MIME_TYPES:
        msg = ("Procession's API works with JSON or YAML. "
               "{0} is not supported.".format(content_type))
        raise fexc.HTTPNotAcceptable(msg)

    return {
        'application/json': deserialize_json,
        'application/yaml': deserialize_yaml
    }[content_type](req.body.read())


def deserialize_json(subject):
    """
    Returns a dict or list of dicts that is deserialized from the supplied
    raw string.

    :param subject: String to deserialize
    """
    try:
        return json.loads(subject, 'utf-8')
    except ValueError:
        msg = ("Could not decode the request body. The JSON was not valid.")
        raise fexc.HTTPBadRequest(msg)


def deserialize_yaml(subject):
    """
    Returns a dict or list of dicts that is deserialized from the supplied
    raw string.

    :param subject: String to deserialize
    """
    try:
        # yaml.load() assumes subject is a UTF-8 encoded str
        return yaml.load(subject)
    except ValueError:
        msg = ("Could not decode the request body. The YAML was not valid.")
        raise fexc.HTTPBadRequest(msg)
