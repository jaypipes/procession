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

import logging

import mock
import testtools
from testtools import matchers

from procession import config
from procession import log


# We cannot use tests.base.UnitTest, because that creates a logging
# fixture that manipulates the log handling for root logger.
class TestApiWsgi(testtools.TestCase):

    def test_log_config_file(self):
        with mock.patch('logging.config.fileConfig') as fc_mock:
            options = {
                'log': {
                    'conf_file': '/some/path'
                },
            }
            conf = config.Config(**options)
            log.init(conf)
            fc_mock.assert_called_once_with('/some/path')

    def test_null_logger_removed_from_root(self):
        nh = logging.NullHandler()
        rl = logging.getLogger()
        rl.setLevel(logging.DEBUG)
        rl.addHandler(nh)
        self.assertThat(rl.handlers, matchers.Contains(nh))
        conf = config.Config()
        log.init(conf)
        self.assertThat(rl.handlers, matchers.Not(matchers.Contains(nh)))
