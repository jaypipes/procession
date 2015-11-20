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

import yaml.parser

from falcon import errors as fexc

from procession import exc
from procession import helpers

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
    :returns string of serialized data or None if serialization fails.

    :raises `falcon.exceptions.HTTPNotAcceptable` if the request does not
            accept one of the acceptable serialization MIME types.
    """
    if isinstance(subject, list):
        if len(subject) > 0 and hasattr(subject[0], 'to_dict'):
            subject = [m.to_dict() for m in subject]
    elif hasattr(subject, 'to_dict'):
        subject = subject.to_dict()

    prefers = req.client_prefers(ALLOWED_MIME_TYPES)
    if prefers is None:
        msg = ("Procession's API works with JSON or YAML. "
               "{0} is not supported.".format(req.accept))
        raise fexc.HTTPNotAcceptable(msg)

    return {
        'application/json': helpers.serialize_json,
        'application/yaml': helpers.serialize_yaml
    }[prefers](subject)


def deserialize(req):
    """
    Returns a dict or list of dicts by reading the supplied request body
    and attempting to deserialize the contents after looking at the request's
    Content-Type header.

    :param request: `falcon.request.Request` object whose body is deserialized

    :raises `falcon.exceptions.HTTPNotAcceptable` if the request content type
            is not an accepted MIME types.
    :raises `procession.exc.BadInput` if deserialization fails.
    """
    if req.content_type is not None:
        content_type = req.content_type.lower()
    else:
        content_type = 'application/json'

    if content_type not in ALLOWED_MIME_TYPES:
        msg = ("Procession's API works with JSON or YAML. "
               "{0} is not supported.".format(content_type))
        raise fexc.HTTPNotAcceptable(msg)

    body = req.stream.read().decode('utf-8')
    return {
        'application/json': helpers.deserialize_json,
        'application/yaml': helpers.deserialize_yaml
    }[content_type](body)
