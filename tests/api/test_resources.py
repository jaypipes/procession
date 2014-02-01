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
        self.mocks = []
        self.resp_mock = fakes.ResponseMock()
        self.patch('procession.api.helpers.serialize', lambda x, y: y)
        super(ResourceTestBase, self).setUp()

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


class OrganizationsResourceTest(ResourceTestBase):

    def setUp(self):
        self.resource = resources.OrganizationsResource()
        super(OrganizationsResourceTest, self).setUp()

    def test_organizations_get(self):
        with mock.patch('procession.api.search.SearchSpec') as ss_mocked:
            with mock.patch('procession.db.api.organizations_get') as og_mocked:
                ss_mocked.return_value = mock.sentinel.spec
                og_mocked.return_value = fakes.FAKE_ORGS

                self.as_auth(self.resource.on_get)

                og_mocked.assert_called_with(self.ctx_mock, mock.sentinel.spec)
                self.assertEquals(self.resp_mock.status, falcon.HTTP_200)
                self.assertEquals(self.resp_mock.body, fakes.FAKE_ORGS)

    def test_organizations_post(self):
        ds_mock = self.patch('procession.api.helpers.deserialize')
        s_mock = self.patch('procession.api.helpers.serialize')
        oc_mock = self.patch('procession.db.api.organization_create')
        gs_mock = self.patch('procession.db.session.get_session')

        oc_mock.return_value = fakes.FAKE_ORG1
        ds_mock.return_value = mock.sentinel.ds
        s_mock.return_value = mock.sentinel.s
        gs_mock.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_post)

        oc_mock.assert_called_once_with(self.ctx_mock,
                                        mock.sentinel.ds,
                                        session=mock.sentinel.sess)
        self.assertEquals(self.resp_mock.status, falcon.HTTP_201)
        s_mock.assert_called_once_with(self.req_mock, fakes.FAKE_ORG1)
        self.assertEquals(self.resp_mock.body, mock.sentinel.s)

    def test_organizations_post_400(self):
        ds_mock = self.patch('procession.api.helpers.deserialize')
        s_mock = self.patch('procession.api.helpers.serialize')
        oc_mock = self.patch('procession.db.api.organization_create')
        gs_mock = self.patch('procession.db.session.get_session')

        oc_mock.side_effect = ValueError
        ds_mock.return_value = mock.sentinel.ds
        s_mock.return_value = mock.sentinel.s
        gs_mock.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_post)

        oc_mock.assert_called_once_with(self.ctx_mock,
                                        mock.sentinel.ds,
                                        session=mock.sentinel.sess)
        self.assertEquals(self.resp_mock.status, falcon.HTTP_400)
        s_mock.assert_not_called()
        self.assertThat(self.resp_mock.body, matchers.Contains('Bad input'))


class OrganizationResourceTest(ResourceTestBase):

    def setUp(self):
        self.resource = resources.OrganizationResource()
        super(OrganizationResourceTest, self).setUp()

    def test_organization_get(self):
        with mock.patch('procession.db.api.organization_get_by_pk') as og_mocked:
            og_mocked.return_value = fakes.FAKE_USER1

            self.as_auth(self.resource.on_get, 123)

            og_mocked.assert_called_with(self.ctx_mock, 123)
            self.assertEquals(self.resp_mock.status, falcon.HTTP_200)
            self.assertEquals(self.resp_mock.body, fakes.FAKE_USER1)

            og_mocked.reset_mock()
            og_mocked.side_effect = exc.NotFound()

            self.as_auth(self.resource.on_get, 123)

            og_mocked.assert_called_with(self.ctx_mock, 123)
            self.assertEquals(self.resp_mock.status, falcon.HTTP_404)

    def test_organization_get_404(self):
        with mock.patch('procession.db.api.organization_get_by_pk') as og_mocked:
            og_mocked.side_effect = exc.NotFound()

            self.as_auth(self.resource.on_get, 123)

            og_mocked.assert_called_with(self.ctx_mock, 123)
            self.assertEquals(self.resp_mock.status, falcon.HTTP_404)

    def test_organizations_delete(self):
        od_mock = self.patch('procession.db.api.organization_delete')
        gs_mock = self.patch('procession.db.session.get_session')

        od_mock.return_value = fakes.FAKE_USER1
        gs_mock.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_delete, 123)

        od_mock.assert_called_once_with(self.ctx_mock,
                                        123,
                                        session=mock.sentinel.sess)
        self.assertEquals(self.resp_mock.status, falcon.HTTP_200)

    def test_organizations_delete_404(self):
        od_mock = self.patch('procession.db.api.organization_delete')
        gs_mock = self.patch('procession.db.session.get_session')

        od_mock.side_effect = exc.NotFound
        gs_mock.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_delete, 123)

        od_mock.assert_called_once_with(self.ctx_mock,
                                        123,
                                        session=mock.sentinel.sess)
        self.assertEquals(self.resp_mock.status, falcon.HTTP_404)


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
        ds_mock = self.patch('procession.api.helpers.deserialize')
        s_mock = self.patch('procession.api.helpers.serialize')
        uc_mock = self.patch('procession.db.api.user_create')
        gs_mock = self.patch('procession.db.session.get_session')

        uc_mock.return_value = fakes.FAKE_USER1
        ds_mock.return_value = mock.sentinel.ds
        s_mock.return_value = mock.sentinel.s
        gs_mock.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_post)

        uc_mock.assert_called_once_with(self.ctx_mock,
                                        mock.sentinel.ds,
                                        session=mock.sentinel.sess)
        self.assertEquals(self.resp_mock.status, falcon.HTTP_201)
        s_mock.assert_called_once_with(self.req_mock, fakes.FAKE_USER1)
        self.assertEquals(self.resp_mock.body, mock.sentinel.s)

    def test_users_post_400(self):
        ds_mock = self.patch('procession.api.helpers.deserialize')
        s_mock = self.patch('procession.api.helpers.serialize')
        uc_mock = self.patch('procession.db.api.user_create')
        gs_mock = self.patch('procession.db.session.get_session')

        uc_mock.side_effect = ValueError
        ds_mock.return_value = mock.sentinel.ds
        s_mock.return_value = mock.sentinel.s
        gs_mock.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_post)

        uc_mock.assert_called_once_with(self.ctx_mock,
                                        mock.sentinel.ds,
                                        session=mock.sentinel.sess)
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
        ds_mock = self.patch('procession.api.helpers.deserialize')
        s_mock = self.patch('procession.api.helpers.serialize')
        uu_mock = self.patch('procession.db.api.user_update')
        gs_mock = self.patch('procession.db.session.get_session')

        uu_mock.return_value = fakes.FAKE_USER1
        ds_mock.return_value = mock.sentinel.ds
        s_mock.return_value = mock.sentinel.s
        gs_mock.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_put, 123)

        uu_mock.assert_called_once_with(self.ctx_mock,
                                        123,
                                        mock.sentinel.ds,
                                        session=mock.sentinel.sess)
        self.assertEquals(self.resp_mock.status, falcon.HTTP_200)
        s_mock.assert_called_once_with(self.req_mock, fakes.FAKE_USER1)
        self.assertEquals(self.resp_mock.body, mock.sentinel.s)

    def test_users_put_404(self):
        ds_mock = self.patch('procession.api.helpers.deserialize')
        s_mock = self.patch('procession.api.helpers.serialize')
        uu_mock = self.patch('procession.db.api.user_update')
        gs_mock = self.patch('procession.db.session.get_session')

        uu_mock.side_effect = exc.NotFound
        ds_mock.return_value = mock.sentinel.ds
        s_mock.return_value = mock.sentinel.s
        gs_mock.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_put, 123)

        uu_mock.assert_called_once_with(self.ctx_mock,
                                        123,
                                        mock.sentinel.ds,
                                        session=mock.sentinel.sess)
        self.assertEquals(self.resp_mock.status, falcon.HTTP_404)
        s_mock.assert_not_called()

    def test_users_delete(self):
        ud_mock = self.patch('procession.db.api.user_delete')
        gs_mock = self.patch('procession.db.session.get_session')

        ud_mock.return_value = fakes.FAKE_USER1
        gs_mock.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_delete, 123)

        ud_mock.assert_called_once_with(self.ctx_mock,
                                        123,
                                        session=mock.sentinel.sess)
        self.assertEquals(self.resp_mock.status, falcon.HTTP_200)

    def test_users_delete_404(self):
        ud_mock = self.patch('procession.db.api.user_delete')
        gs_mock = self.patch('procession.db.session.get_session')

        ud_mock.side_effect = exc.NotFound
        gs_mock.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_delete, 123)

        ud_mock.assert_called_once_with(self.ctx_mock,
                                        123,
                                        session=mock.sentinel.sess)
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
        ds_mock = self.patch('procession.api.helpers.deserialize')
        s_mock = self.patch('procession.api.helpers.serialize')
        uc_mock = self.patch('procession.db.api.user_key_create')
        gs_mock = self.patch('procession.db.session.get_session')

        key_mock = mock.MagicMock()
        key_mock.id = 567
        uc_mock.return_value = key_mock
        ds_mock.return_value = mock.sentinel.ds
        s_mock.return_value = mock.sentinel.s
        gs_mock.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_post, 123)

        uc_mock.assert_called_once_with(self.ctx_mock,
                                        123,
                                        mock.sentinel.ds,
                                        session=mock.sentinel.sess)
        self.assertEquals(self.resp_mock.status, falcon.HTTP_201)
        s_mock.assert_called_once_with(self.req_mock, key_mock)
        self.assertEquals(self.resp_mock.body, mock.sentinel.s)
        self.assertEquals(self.resp_mock.location, "/users/123/keys/567")

    def test_user_keys_post_400(self):
        ds_mock = self.patch('procession.api.helpers.deserialize')
        s_mock = self.patch('procession.api.helpers.serialize')
        uc_mock = self.patch('procession.db.api.user_key_create')
        gs_mock = self.patch('procession.db.session.get_session')

        key_mock = mock.MagicMock()
        key_mock.id = 567
        uc_mock.side_effect = ValueError
        ds_mock.return_value = mock.sentinel.ds
        s_mock.return_value = mock.sentinel.s
        gs_mock.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_post, 123)

        uc_mock.assert_called_once_with(self.ctx_mock,
                                        123,
                                        mock.sentinel.ds,
                                        session=mock.sentinel.sess)
        self.assertEquals(self.resp_mock.status, falcon.HTTP_400)
        s_mock.assert_not_called()

    def test_user_keys_post_no_user_404(self):
        ds_mock = self.patch('procession.api.helpers.deserialize')
        s_mock = self.patch('procession.api.helpers.serialize')
        uc_mock = self.patch('procession.db.api.user_key_create')
        gs_mock = self.patch('procession.db.session.get_session')

        key_mock = mock.MagicMock()
        key_mock.id = 567
        uc_mock.side_effect = exc.NotFound
        ds_mock.return_value = mock.sentinel.ds
        s_mock.return_value = mock.sentinel.s
        gs_mock.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_post, 123)

        uc_mock.assert_called_once_with(self.ctx_mock,
                                        123,
                                        mock.sentinel.ds,
                                        session=mock.sentinel.sess)
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
        uk_mock = self.patch('procession.db.api.user_key_delete')
        gs_mock = self.patch('procession.db.session.get_session')

        uk_mock.return_value = fakes.FAKE_USER1
        gs_mock.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_delete, 123, 'ABC')

        uk_mock.assert_called_once_with(self.ctx_mock,
                                        123, 'ABC',
                                        session=mock.sentinel.sess)
        self.assertEquals(self.resp_mock.status, falcon.HTTP_200)

    def test_users_delete_404(self):
        uk_mock = self.patch('procession.db.api.user_key_delete')
        gs_mock = self.patch('procession.db.session.get_session')

        uk_mock.side_effect = exc.NotFound
        gs_mock.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_delete, 123, 'ABC')

        uk_mock.assert_called_once_with(self.ctx_mock,
                                        123, 'ABC',
                                        session=mock.sentinel.sess)
        self.assertEquals(self.resp_mock.status, falcon.HTTP_404)
