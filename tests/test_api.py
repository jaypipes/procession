#!/usr/bin/env python
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

import fixtures
import os
import testtools

from procession import api
from oslo.config import cfg

CONF = cfg.CONF
PECAN_CONFIG = os.path.join(os.path.dirname(__file__), 'etc', 'pecan.py')


class TestApi(testtools.TestCase):

    def setUp(self):
        self.useFixture(fixtures.FakeLogger())
        self.orig_cfg = CONF.api.pecan_config_file
        CONF.api.pecan_config_file = PECAN_CONFIG
        super(TestApi, self).setUp()

    def tearDown(self):
        super(TestApi, self).tearDown()
        CONF.api.pecan_config_file = self.orig_cfg

    def test_api_setup_app(self):
        app = api.setup_app()
        self.assertTrue(app is not None)
