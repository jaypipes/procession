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

import pprint

import falcon
import mock
from testtools import matchers
from testtools import content as ttcontent

from procession.api import resources
from procession import exc

from tests import fakes
from tests import base


class ResourceTestBase(base.UnitTest):

    """
    This test case base class that stresses the logic of the various API
    resources. For HTTP/WSGI tests, see test_api.py.
    """

    def setUp(self):
        self.patchers = []
        self.resp_mock = fakes.ResponseMock()
        self.patch('procession.api.helpers.serialize', lambda x, y: y)
        super(ResourceTestBase, self).setUp()

    def tearDown(self):
        super(ResourceTestBase, self).tearDown()
        for p in self.patchers:
            p.stop()

    def patch(self, patched, *args, **kwargs):
        patcher = mock.patch(patched, *args, **kwargs)
        patcher.start()
        self.patchers.append(patcher)

    def add_body_detail(self):
        formatted = pprint.pformat(self.resp_mock.body, indent=2)
        self.addDetail('response-body', ttcontent.text_content(formatted))

    def as_anon(self, resource_method, *args, **kwargs):
        """
        Calls the supplied resource method, passing in a non-authenticated
        request object.
        """
        self.req_mock = fakes.AnonymousRequestMock()
        self.ctx_mock = self.req_mock.context
        resource_method(self.req_mock, self.resp_mock, *args, **kwargs)
        self.add_body_detail()

    def as_auth(self, resource_method, *args, **kwargs):
        """
        Calls the supplied resource method, passing in an authenticated
        request object.
        """
        self.req_mock = fakes.AuthenticatedRequestMock()
        self.ctx_mock = self.req_mock.context
        resource_method(self.req_mock, self.resp_mock, *args, **kwargs)
        self.add_body_detail()


class VersionsResourceTest(ResourceTestBase):

    def setUp(self):
        self.resource = resources.VersionsResource()
        super(VersionsResourceTest, self).setUp()

    def test_versions_have_one_current(self):
        self.as_anon(self.resource.on_get)
        versions = self.resp_mock.body
        self.assertEquals(self.resp_mock.status, falcon.HTTP_302)
        self.assertThat(versions, matchers.IsInstance(list))
        self.assertThat(len(versions), matchers.GreaterThan(0))
        self.assertThat(versions[0], matchers.IsInstance(dict))
        self.assertIn('current', versions[0].keys())
        self.assertThat([v for v in versions if v['current'] is True],
                        matchers.HasLength(1))


class UsersResourceTest(ResourceTestBase):

    def setUp(self):
        self.resource = resources.UsersResource()
        super(UsersResourceTest, self).setUp()

    def test_users_get(self):
        with mock.patch('procession.api.search.SearchSpec') as ss_mocked:
            with mock.patch('procession.db.api.users_get') as ug_mocked:
                ss_mocked.return_value = mock.sentinel.spec
                ug_mocked.return_value = fakes.FAKE_USERS

                self.as_auth(self.resource.on_get)

                ug_mocked.assert_called_with(self.ctx_mock, mock.sentinel.spec)
                self.assertEquals(self.resp_mock.status, falcon.HTTP_200)
                self.assertEquals(self.resp_mock.body, fakes.FAKE_USERS)

    def test_users_post(self):
        ds_patcher = mock.patch('procession.api.helpers.deserialize')
        s_patcher = mock.patch('procession.api.helpers.serialize')
        uc_patcher = mock.patch('procession.db.api.user_create')
        gs_patcher = mock.patch('procession.db.session.get_session')

        ds_mock = ds_patcher.start()
        s_mock = s_patcher.start()
        uc_mock = uc_patcher.start()
        gs_mock = gs_patcher.start()

        self.addCleanup(ds_patcher.stop)
        self.addCleanup(s_patcher.stop)
        self.addCleanup(uc_patcher.stop)
        self.addCleanup(gs_patcher.stop)

        sess_mock = mock.MagicMock()

        uc_mock.return_value = fakes.FAKE_USER1
        ds_mock.return_value = mock.sentinel.ds
        s_mock.return_value = mock.sentinel.s
        gs_mock.return_value = sess_mock

        self.as_auth(self.resource.on_post)

        uc_mock.assert_called_once_with(self.ctx_mock,
                                        mock.sentinel.ds,
                                        session=sess_mock)
        sess_mock.commit.assert_called_once_with()
        self.assertEquals(self.resp_mock.status, falcon.HTTP_201)
        s_mock.assert_called_once_with(self.req_mock, fakes.FAKE_USER1)
        self.assertEquals(self.resp_mock.body, mock.sentinel.s)


class UserResourceTest(ResourceTestBase):

    def setUp(self):
        self.resource = resources.UserResource()
        super(UserResourceTest, self).setUp()

    def test_user_get(self):
        with mock.patch('procession.db.api.user_get_by_id') as ug_mocked:
            ug_mocked.return_value = fakes.FAKE_USERS

            self.as_auth(self.resource.on_get, 123)

            ug_mocked.assert_called_with(self.ctx_mock, 123)
            self.assertEquals(self.resp_mock.status, falcon.HTTP_200)
            self.assertEquals(self.resp_mock.body, fakes.FAKE_USERS)

            ug_mocked.reset_mock()
            ug_mocked.side_effect = exc.NotFound()

            self.as_auth(self.resource.on_get, 123)

            ug_mocked.assert_called_with(self.ctx_mock, 123)
            self.assertEquals(self.resp_mock.status, falcon.HTTP_404)
