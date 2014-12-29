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

import json
import uuid
import yaml


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


def deserialize_json(subject):
    """
    Returns a dict or list of dicts that is deserialized from the supplied
    raw string.

    :param subject: String to deserialize
    """
    return json.loads(subject, 'utf-8')


def deserialize_yaml(subject):
    """
    Returns a dict or list of dicts that is deserialized from the supplied
    raw string.

    :param subject: String to deserialize
    """
    # yaml.load() assumes subject is a UTF-8 encoded str
    return yaml.load(subject)


def is_like_int(subject):
    """
    Returns True if the subject resembles an integer, False otherwise.
    """
    if isinstance(subject, int):
        return True
    try:
        return str(int(subject)) == subject
    except (TypeError, ValueError, AttributeError):
        return False


def is_like_uuid(subject):
    """
    Returns True if the subject resembles a UUID, False otherwise.
    """
    if isinstance(subject, uuid.UUID):
        return True
    try:
        return str(uuid.UUID(subject)) == subject
    except (TypeError, ValueError, AttributeError):
        return False


def ordered_uuid():
    """
    Returns a UUID type 1 value, with the more constant segments of the
    UUID at the start of the UUID. This allows us to have mostly monotonically
    increasing UUID values, which are much better for INSERT/UPDATE performance
    in the DB.

    A UUID1 hex looks like:

        '27392da2-8bae-11e4-961d-e06995034837'

    From this, we need to take the last two segments, which represent the more
    constant information about the node we're on, and place those first in the
    new UUID's bytes. We then take the '11e4' segment, which represents the
    most significant bits of the timestamp part of the UUID, prefixed with a
    '1' for UUID type, and place that next, followed by the second segment and
    finally the first segment, which are the next most significant bits of the
    timestamp 60-bit number embedded in the UUID.

    So, we convert the above hex to this instead:

        '961de069-9503-4837-11e4-8bae27392da2'

    """
    val = uuid.uuid1().hex
    new_val = val[16:] + val[12:16] + val[8:12] + val[0:8]
    return uuid.UUID(new_val)
