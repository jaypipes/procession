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
Simple log setup routines. In order to prevent spurious, non-routed
log records, this module should be imported early in the import process.
"""

import logging
import logging.config
import logging.handlers
import sys


DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_LOG_FORMAT = ("%(asctime)s.%(msecs)03d %(process)d %(levelname)s "
                      "%(name)s %(message)s")


if len(logging.root.handlers) == 0:
    # The logging system has yet to be set up, so here
    # we just ensure that some log handler is around to
    # prevent "No handlers could be found for logger 'blah'"
    # messages...
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger().addHandler(logging.NullHandler())


def setup(**kwargs):
    """
    Sets up logging facilities for Procession. We do some initial
    cleanup of the null logger handler and then handle any options
    supplied:

    `conf_file`:
        Optional path to a Python logging config file. If
        present, we simply load logging settings from this
        file and exit.
    `log_level`:
        Optional string for the level of logging to log.
        Defaults to 'error'. Should match one of the string log
        levels for standard Python logging.
    `date_format`:
        Optional string formatter for datetime strings in
        log records. Defaults to DEFAULT_DATE_FORMAT.
    `log_format`:
        Optional string formatter for log records. Defaults to
        DEFAULT_LOG_FORMAT.
    """

    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        if isinstance(handler, logging.NullHandler):
            root_logger.removeHandler(handler)

    conf_file = kwargs.get('conf_file')
    if conf_file:
        logging.config.fileConfig(conf_file)
        return

    date_format = kwargs.get('date_format', DEFAULT_DATE_FORMAT)
    log_format = kwargs.get('log_format', DEFAULT_LOG_FORMAT)
    log_level = getattr(logging, kwargs.get('log_level', 'error').upper())

    handler = None
    for handler in root_logger.handlers:
        # NullHandler does not have a stream attribute...
        if hasattr(handler, 'stream') and handler.stream is sys.stderr:
            break
    else:
        handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(log_level)

    formatter = logging.Formatter(log_format, datefmt=date_format)

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
