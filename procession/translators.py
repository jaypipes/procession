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

_ISO8601_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S+00:00'
if six.PY2:
    class UTC(datetime.tzinfo):
        """
        Python 2.7 doesn't have a datetime.timezone module with a utc object.
        """
        _ZERO = datetime.timedelta(0)

        def utcoffset(self, dt):
            return self._ZERO

        def tzname(self, dt):
            return "UTC"

        def dst(self, dt):
            return self._ZERO

    _UTC = UTC()
else:
    _UTC = datetime.timezone.utc


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
    """
    Return a `datetime.datetime` object from a supplied datetime or string.

    :note The returned `datetime.datetime` object will have a UTC timezone.
    """
    if isinstance(subject, datetime.datetime):
        return subject
    if isinstance(subject, six.string_types):
        return datetime.datetime.strptime(subject, _ISO8601_TIME_FORMAT)
    if isinstance(subject, float):
        return datetime.datetime.utcfromtimestamp(subject)
    raise ValueError(six.text_type(subject))


def coerce_iso8601_string(subject):
    """
    Return a string in the format of an ISO-8601 timestamp in UTC timezone:

        YYYY-MM-DDTHH:MM:SS+00:00

    :note If the supplied subject is a `datetime.datetime` object and has no
          timezone component, the tzinfo will be set to UTC and then converted
          to a string.
    """
    if isinstance(subject, datetime.datetime):
        if subject.tzinfo is None:
            subject = subject.replace(tzinfo=_UTC)
        return subject.isoformat()
    return parse_isotime(subject).isoformat()
coerce_iso8601_string.reverser = coerce_datetime


def coerce_nullstring_to_none(subject):
    """
    Returns None if the supplied subject is a nullstring (''), otherwise
    returns the subject unchanged if it's a string type.
    """
    if isinstance(subject, (six.string_types, six.binary_type)):
        if subject in (six.text_type(''), six.b('')):
            return None
        return subject
    msg = "%r is not a string or binary type." % subject
    raise ValueError(msg)


def coerce_none_to_nullstring(subject):
    """
    Returns a nullstring ('') if the subject is None, otherwise returns the
    subject unchanged it it's a string type.
    """
    if subject is None:
        return ''
    if isinstance(subject, (six.string_types, six.binary_type)):
        return subject
    msg = "%r is not a string or binary type." % subject
    raise ValueError(msg)
coerce_none_to_nullstring.reverser = coerce_nullstring_to_none
