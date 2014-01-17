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

    def test_users_post_400(self):
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

        uc_mock.side_effect = ValueError
        ds_mock.return_value = mock.sentinel.ds
        s_mock.return_value = mock.sentinel.s
        gs_mock.return_value = sess_mock

        self.as_auth(self.resource.on_post)

        uc_mock.assert_called_once_with(self.ctx_mock,
                                        mock.sentinel.ds,
                                        session=sess_mock)
        sess_mock.commit.assert_not_called()
        self.assertEquals(self.resp_mock.status, falcon.HTTP_400)
        s_mock.assert_not_called()
        self.assertThat(self.resp_mock.body, matchers.Contains('Bad input'))


class UserResourceTest(ResourceTestBase):

    def setUp(self):
        self.resource = resources.UserResource()
        super(UserResourceTest, self).setUp()

    def test_user_get(self):
        with mock.patch('procession.db.api.user_get_by_pk') as ug_mocked:
            ug_mocked.return_value = fakes.FAKE_USER1

            self.as_auth(self.resource.on_get, 123)

            ug_mocked.assert_called_with(self.ctx_mock, 123)
            self.assertEquals(self.resp_mock.status, falcon.HTTP_200)
            self.assertEquals(self.resp_mock.body, fakes.FAKE_USER1)

            ug_mocked.reset_mock()
            ug_mocked.side_effect = exc.NotFound()

            self.as_auth(self.resource.on_get, 123)

            ug_mocked.assert_called_with(self.ctx_mock, 123)
            self.assertEquals(self.resp_mock.status, falcon.HTTP_404)

    def test_user_get_404(self):
        with mock.patch('procession.db.api.user_get_by_pk') as ug_mocked:
            ug_mocked.side_effect = exc.NotFound()

            self.as_auth(self.resource.on_get, 123)

            ug_mocked.assert_called_with(self.ctx_mock, 123)
            self.assertEquals(self.resp_mock.status, falcon.HTTP_404)

    def test_users_put(self):
        ds_patcher = mock.patch('procession.api.helpers.deserialize')
        s_patcher = mock.patch('procession.api.helpers.serialize')
        uu_patcher = mock.patch('procession.db.api.user_update')
        gs_patcher = mock.patch('procession.db.session.get_session')

        ds_mock = ds_patcher.start()
        s_mock = s_patcher.start()
        uu_mock = uu_patcher.start()
        gs_mock = gs_patcher.start()

        self.addCleanup(ds_patcher.stop)
        self.addCleanup(s_patcher.stop)
        self.addCleanup(uu_patcher.stop)
        self.addCleanup(gs_patcher.stop)

        sess_mock = mock.MagicMock()

        uu_mock.return_value = fakes.FAKE_USER1
        ds_mock.return_value = mock.sentinel.ds
        s_mock.return_value = mock.sentinel.s
        gs_mock.return_value = sess_mock

        self.as_auth(self.resource.on_put, 123)

        uu_mock.assert_called_once_with(self.ctx_mock,
                                        123,
                                        mock.sentinel.ds,
                                        session=sess_mock)
        sess_mock.commit.assert_called_once_with()
        self.assertEquals(self.resp_mock.status, falcon.HTTP_200)
        s_mock.assert_called_once_with(self.req_mock, fakes.FAKE_USER1)
        self.assertEquals(self.resp_mock.body, mock.sentinel.s)

    def test_users_put_404(self):
        ds_patcher = mock.patch('procession.api.helpers.deserialize')
        s_patcher = mock.patch('procession.api.helpers.serialize')
        uu_patcher = mock.patch('procession.db.api.user_update')
        gs_patcher = mock.patch('procession.db.session.get_session')

        ds_mock = ds_patcher.start()
        s_mock = s_patcher.start()
        uu_mock = uu_patcher.start()
        gs_mock = gs_patcher.start()

        self.addCleanup(ds_patcher.stop)
        self.addCleanup(s_patcher.stop)
        self.addCleanup(uu_patcher.stop)
        self.addCleanup(gs_patcher.stop)

        sess_mock = mock.MagicMock()

        uu_mock.side_effect = exc.NotFound
        ds_mock.return_value = mock.sentinel.ds
        s_mock.return_value = mock.sentinel.s
        gs_mock.return_value = sess_mock

        self.as_auth(self.resource.on_put, 123)

        uu_mock.assert_called_once_with(self.ctx_mock,
                                        123,
                                        mock.sentinel.ds,
                                        session=sess_mock)
        sess_mock.commit.assert_not_called()
        self.assertEquals(self.resp_mock.status, falcon.HTTP_404)
        s_mock.assert_not_called()

    def test_users_delete(self):
        ud_patcher = mock.patch('procession.db.api.user_delete')
        gs_patcher = mock.patch('procession.db.session.get_session')

        ud_mock = ud_patcher.start()
        gs_mock = gs_patcher.start()

        self.addCleanup(ud_patcher.stop)
        self.addCleanup(gs_patcher.stop)

        sess_mock = mock.MagicMock()

        ud_mock.return_value = fakes.FAKE_USER1
        gs_mock.return_value = sess_mock

        self.as_auth(self.resource.on_delete, 123)

        ud_mock.assert_called_once_with(self.ctx_mock,
                                        123,
                                        session=sess_mock)
        sess_mock.commit.assert_called_once_with()
        self.assertEquals(self.resp_mock.status, falcon.HTTP_200)

    def test_users_delete_404(self):
        ud_patcher = mock.patch('procession.db.api.user_delete')
        gs_patcher = mock.patch('procession.db.session.get_session')

        ud_mock = ud_patcher.start()
        gs_mock = gs_patcher.start()

        self.addCleanup(ud_patcher.stop)
        self.addCleanup(gs_patcher.stop)

        sess_mock = mock.MagicMock()

        ud_mock.side_effect = exc.NotFound
        gs_mock.return_value = sess_mock

        self.as_auth(self.resource.on_delete, 123)

        ud_mock.assert_called_once_with(self.ctx_mock,
                                        123,
                                        session=sess_mock)
        sess_mock.commit.assert_not_called()
        self.assertEquals(self.resp_mock.status, falcon.HTTP_404)


class UserKeysResourceTest(ResourceTestBase):

    def setUp(self):
        self.resource = resources.UserKeysResource()
        super(UserKeysResourceTest, self).setUp()

    def test_user_keys_get(self):
        with mock.patch('procession.api.search.SearchSpec') as ss_mocked:
            with mock.patch('procession.db.api.user_keys_get') as ug_mocked:
                spec = mock.MagicMock()
                filters_mock = mock.PropertyMock()
                type(spec).filters = filters_mock
                ss_mocked.return_value = spec
                ug_mocked.return_value = mock.sentinel.keys

                self.as_auth(self.resource.on_get, 123)

                filters_mock.assert_called_with()
                ug_mocked.assert_called_with(self.ctx_mock, spec)
                self.assertEquals(self.resp_mock.status, falcon.HTTP_200)
                self.assertEquals(self.resp_mock.body, mock.sentinel.keys)

    def test_user_keys_post(self):
        ds_patcher = mock.patch('procession.api.helpers.deserialize')
        s_patcher = mock.patch('procession.api.helpers.serialize')
        uc_patcher = mock.patch('procession.db.api.user_key_create')
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

        key_mock = mock.MagicMock()
        key_mock.id = 567
        uc_mock.return_value = key_mock
        ds_mock.return_value = mock.sentinel.ds
        s_mock.return_value = mock.sentinel.s
        gs_mock.return_value = sess_mock

        self.as_auth(self.resource.on_post, 123)

        uc_mock.assert_called_once_with(self.ctx_mock,
                                        123,
                                        mock.sentinel.ds,
                                        session=sess_mock)
        sess_mock.commit.assert_called_once_with()
        self.assertEquals(self.resp_mock.status, falcon.HTTP_201)
        s_mock.assert_called_once_with(self.req_mock, key_mock)
        self.assertEquals(self.resp_mock.body, mock.sentinel.s)
        self.assertEquals(self.resp_mock.location, "/users/123/keys/567")

    def test_user_keys_post_400(self):
        ds_patcher = mock.patch('procession.api.helpers.deserialize')
        s_patcher = mock.patch('procession.api.helpers.serialize')
        uc_patcher = mock.patch('procession.db.api.user_key_create')
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

        key_mock = mock.MagicMock()
        key_mock.id = 567
        uc_mock.side_effect = ValueError
        ds_mock.return_value = mock.sentinel.ds
        s_mock.return_value = mock.sentinel.s
        gs_mock.return_value = sess_mock

        self.as_auth(self.resource.on_post, 123)

        uc_mock.assert_called_once_with(self.ctx_mock,
                                        123,
                                        mock.sentinel.ds,
                                        session=sess_mock)
        sess_mock.commit.assert_not_called()
        self.assertEquals(self.resp_mock.status, falcon.HTTP_400)
        s_mock.assert_not_called()

    def test_user_keys_post_no_user_404(self):
        ds_patcher = mock.patch('procession.api.helpers.deserialize')
        s_patcher = mock.patch('procession.api.helpers.serialize')
        uc_patcher = mock.patch('procession.db.api.user_key_create')
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

        key_mock = mock.MagicMock()
        key_mock.id = 567
        uc_mock.side_effect = exc.NotFound
        ds_mock.return_value = mock.sentinel.ds
        s_mock.return_value = mock.sentinel.s
        gs_mock.return_value = sess_mock

        self.as_auth(self.resource.on_post, 123)

        uc_mock.assert_called_once_with(self.ctx_mock,
                                        123,
                                        mock.sentinel.ds,
                                        session=sess_mock)
        sess_mock.commit.assert_not_called()
        self.assertEquals(self.resp_mock.status, falcon.HTTP_404)
        s_mock.assert_not_called()


class UserKeyResourceTest(ResourceTestBase):

    def setUp(self):
        self.resource = resources.UserKeyResource()
        super(UserKeyResourceTest, self).setUp()

    def test_user_key_get(self):
        with mock.patch('procession.db.api.user_key_get_by_pk') as uk_mocked:
            uk_mocked.return_value = fakes.FAKE_KEY1

            self.as_auth(self.resource.on_get, 123, 'ABC')

            uk_mocked.assert_called_with(self.ctx_mock, 123, 'ABC')
            self.assertEquals(self.resp_mock.status, falcon.HTTP_200)
            self.assertEquals(self.resp_mock.body, fakes.FAKE_KEY1)

            uk_mocked.reset_mock()
            uk_mocked.side_effect = exc.NotFound()

            self.as_auth(self.resource.on_get, 123, 'ABC')

            uk_mocked.assert_called_with(self.ctx_mock, 123, 'ABC')
            self.assertEquals(self.resp_mock.status, falcon.HTTP_404)

    def test_user_key_get_404(self):
        with mock.patch('procession.db.api.user_key_get_by_pk') as uk_mocked:
            uk_mocked.side_effect = exc.NotFound()

            self.as_auth(self.resource.on_get, 123, 'ABC')

            uk_mocked.assert_called_with(self.ctx_mock, 123, 'ABC')
            self.assertEquals(self.resp_mock.status, falcon.HTTP_404)

    def test_user_key_delete(self):
        uk_patcher = mock.patch('procession.db.api.user_key_delete')
        gs_patcher = mock.patch('procession.db.session.get_session')

        uk_mock = uk_patcher.start()
        gs_mock = gs_patcher.start()

        self.addCleanup(uk_patcher.stop)
        self.addCleanup(gs_patcher.stop)

        sess_mock = mock.MagicMock()

        uk_mock.return_value = fakes.FAKE_USER1
        gs_mock.return_value = sess_mock

        self.as_auth(self.resource.on_delete, 123, 'ABC')

        uk_mock.assert_called_once_with(self.ctx_mock,
                                        123, 'ABC',
                                        session=sess_mock)
        sess_mock.commit.assert_called_once_with()
        self.assertEquals(self.resp_mock.status, falcon.HTTP_200)

    def test_users_delete_404(self):
        uk_patcher = mock.patch('procession.db.api.user_key_delete')
        gs_patcher = mock.patch('procession.db.session.get_session')

        uk_mock = uk_patcher.start()
        gs_mock = gs_patcher.start()

        self.addCleanup(uk_patcher.stop)
        self.addCleanup(gs_patcher.stop)

        sess_mock = mock.MagicMock()

        uk_mock.side_effect = exc.NotFound
        gs_mock.return_value = sess_mock

        self.as_auth(self.resource.on_delete, 123, 'ABC')

        uk_mock.assert_called_once_with(self.ctx_mock,
                                        123, 'ABC',
                                        session=sess_mock)
        sess_mock.commit.assert_not_called()
        self.assertEquals(self.resp_mock.status, falcon.HTTP_404)
