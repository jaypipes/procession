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

from oslo.config import cfg
import pecan

from procession.api import hooks

api_opts = [
    cfg.StrOpt('pecan_config_file',
               default='/etc/processiond/pecan.py',
               help='Filepath to the pecan configuration file.')
]

CONF = cfg.CONF
CONF.register_opts(api_opts, 'api')


def _get_pecan_config():
    return pecan.configuration.conf_from_file(CONF.api.pecan_config_file)


def setup_app(**kwargs):
    app_hooks = [hooks.ConfigHook()]

    pecan_config = kwargs.get('pecan_config', _get_pecan_config())

    pecan.configuration.set_config(dict(pecan_config), overwrite=True)

    make_app_args = dict(
        template_path=pecan_config.app.template_path,
        debug=CONF.debug,
        force_canonical=getattr(pecan_config.app, 'force_canonical', True),
        hooks=app_hooks
    )
    if CONF.debug:
        # Avoid an annoying RuntimeWarning if debug is False and static_root
        # keyword argument is specified.
        make_app_args['static_root'] = pecan_config.app.static_root
    app = pecan.make_app(pecan_config.app.root, **make_app_args)
    return app
