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

VERSION_HEADER = 'X-Procession-API-Version'
HISTORY = {
    (1, 0): "Initial Procession REST API version.",
}

LATEST = max(HISTORY.keys())


def to_tuple(subject):
    if type(subject) == tuple:
        return subject
    else:
        major, minor = subject.split('.')
        return int(major), int(minor)


def tuple_from_request(req):
    """
    Returns a version tuple representing the API version that the user has
    requested, or the latest API version if not specified.

    :param request: `falcon.request.Request` object.
    """
    header_val = req.get_header(VERSION_HEADER)
    if header_val is not None:
        return to_tuple(header_val)
    else:
        return LATEST
