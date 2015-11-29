# -*- encoding: utf-8 -*-
#
# Copyright 2015 Jay Pipes
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

import iso8601
import six


def parse_isotime(timestr):
    """
    Parse time from ISO 8601 format.

    :note This code verbatim from `oslo_utils.timeutils` module.
          Apache 2 licensed.
    """
    try:
        return iso8601.parse_date(timestr)
    except iso8601.ParseError as e:
        raise ValueError(six.text_type(e))
    except TypeError as e:
        raise ValueError(six.text_type(e))


def coerce_datetime(subject):
    if isinstance(subject, datetime.datetime):
        return subject
    if isinstance(subject, six.string_types):
        return datetime.datetime.utcfromtimestamp(subject).isoformat()
    raise ValueError(six.text_type(subject))


def coerce_iso8601_string(subject):
    if isinstance(subject, datetime.datetime):
        if subject.tzinfo is None:
            subject = subject.replace(tzinfo=datetime.timezone.utc)
        return subject.isoformat()
    return parse_isotime(subject).isoformat()
coerce_iso8601_string.reverser = coerce_datetime
