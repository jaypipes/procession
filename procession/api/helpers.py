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

from procession.db import models


def serialize(subject, out_format='json'):
    """
    Returns a serialized string representing the supplied subject. We do some
    introspection of the supplied subject to convert the subject to a dict or
    list of dicts if the subject is not already a dict or list of dicts.

    :param subject: The thing or things to serialize
    :param out_format: String indicating output format for serialization
    """
    if isinstance(subject, list):
        if len(subject) > 0 and isinstance(subject[0], models.ModelBase):
            subject = [m.to_dict() for m in subject]

    return {
        'json': serialize_json,
        'yaml': serialize_yaml
    }[out_format](subject)


def serialize_json(subject):
    """
    Returns a JSON-serialized string representing the supplied dict or
    list of dicts.

    :param subject: dict or list of dicts to serialize
    """
    return json.dumps(subject)


def serialize_yaml(subject):
    """
    Returns a JSON-serialized string representing the supplied dict or
    list of dicts.

    :param subject: dict or list of dicts to serialize
    """
    return yaml.dump(subject)
