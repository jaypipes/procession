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


def serialize(models, out_format='json'):
    """
    Returns a serialized string representing the supplied single or list
    of models.

    :param models: A list of models or a single model
    """
    return {
        'json': serialize_json
    }[out_format](models)


def serialize_yaml(models):
    """
    Returns a YAML-serialized string representing the supplied single or
    list of models.

    :param models: A list of models or a single model
    """
    if isinstance(models, list):
        return yaml.dump([m.to_dict() for m in models])
    return yaml.dump(m.to_dict())


def serialize_json(models):
    """
    Returns a JSON-serialized string representing the supplied single or
    list of models.

    :param models: A list of models or a single model
    """
    if isinstance(models, list):
        return json.dumps([m.to_dict() for m in models])
    return json.dumps(m.to_dict())
