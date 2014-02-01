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
        self.resp = fakes.ResponseMock()
        self.patch('procession.api.helpers.serialize', lambda x, y: y)
        super(ResourceTestBase, self).setUp()

    def add_body_detail(self):
        formatted = pprint.pformat(self.resp.body, indent=2)
        self.addDetail('response-body', ttcontent.text_content(formatted))

    def as_anon(self, resource_method, *args, **kwargs):
        """
        Calls the supplied resource method, passing in a non-authenticated
        request object.
        """
        self.req = fakes.AnonymousRequestMock()
        self.ctx = self.req.context
        resource_method(self.req, self.resp, *args, **kwargs)
        self.add_body_detail()

    def as_auth(self, resource_method, *args, **kwargs):
        """
        Calls the supplied resource method, passing in an authenticated
        request object.
        """
        self.req = fakes.AuthenticatedRequestMock()
        self.ctx = self.req.context
        resource_method(self.req, self.resp, *args, **kwargs)
        self.add_body_detail()


class VersionsResourceTest(ResourceTestBase):

    def setUp(self):
        self.resource = resources.VersionsResource()
        super(VersionsResourceTest, self).setUp()

    def test_versions_have_one_current(self):
        self.as_anon(self.resource.on_get)
        versions = self.resp.body
        self.assertEquals(self.resp.status, falcon.HTTP_302)
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
        with mock.patch('procession.api.search.SearchSpec') as ss:
            with mock.patch('procession.db.api.organizations_get') as og:
                ss.return_value = mock.sentinel.spec
                og.return_value = fakes.FAKE_ORGS

                self.as_auth(self.resource.on_get)

                og.assert_called_with(self.ctx, mock.sentinel.spec)
                self.assertEquals(self.resp.status, falcon.HTTP_200)
                self.assertEquals(self.resp.body, fakes.FAKE_ORGS)

    def test_organizations_post(self):
        ds = self.patch('procession.api.helpers.deserialize')
        s = self.patch('procession.api.helpers.serialize')
        oc = self.patch('procession.db.api.organization_create')
        gs = self.patch('procession.db.session.get_session')

        oc.return_value = fakes.FAKE_ORG1
        ds.return_value = mock.sentinel.ds
        s.return_value = mock.sentinel.s
        gs.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_post)

        oc.assert_called_once_with(self.ctx, mock.sentinel.ds,
                                   session=mock.sentinel.sess)
        self.assertEquals(self.resp.status, falcon.HTTP_201)
        s.assert_called_once_with(self.req, fakes.FAKE_ORG1)
        self.assertEquals(self.resp.body, mock.sentinel.s)

    def test_organizations_post_400(self):
        ds = self.patch('procession.api.helpers.deserialize')
        s = self.patch('procession.api.helpers.serialize')
        oc = self.patch('procession.db.api.organization_create')
        gs = self.patch('procession.db.session.get_session')

        oc.side_effect = ValueError
        ds.return_value = mock.sentinel.ds
        s.return_value = mock.sentinel.s
        gs.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_post)

        oc.assert_called_once_with(self.ctx, mock.sentinel.ds,
                                   session=mock.sentinel.sess)
        self.assertEquals(self.resp.status, falcon.HTTP_400)
        s.assert_not_called()
        self.assertThat(self.resp.body, matchers.Contains('Bad input'))


class OrganizationResourceTest(ResourceTestBase):

    def setUp(self):
        self.resource = resources.OrganizationResource()
        super(OrganizationResourceTest, self).setUp()

    def test_organization_get(self):
        with mock.patch('procession.db.api.organization_get_by_pk') as og:
            og.return_value = fakes.FAKE_USER1

            self.as_auth(self.resource.on_get, 123)

            og.assert_called_with(self.ctx, 123)
            self.assertEquals(self.resp.status, falcon.HTTP_200)
            self.assertEquals(self.resp.body, fakes.FAKE_USER1)

            og.reset()
            og.side_effect = exc.NotFound()

            self.as_auth(self.resource.on_get, 123)

            og.assert_called_with(self.ctx, 123)
            self.assertEquals(self.resp.status, falcon.HTTP_404)

    def test_organization_get_404(self):
        with mock.patch('procession.db.api.organization_get_by_pk') as og:
            og.side_effect = exc.NotFound()

            self.as_auth(self.resource.on_get, 123)

            og.assert_called_with(self.ctx, 123)
            self.assertEquals(self.resp.status, falcon.HTTP_404)

    def test_organizations_delete(self):
        od = self.patch('procession.db.api.organization_delete')
        gs = self.patch('procession.db.session.get_session')

        od.return_value = fakes.FAKE_USER1
        gs.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_delete, 123)

        od.assert_called_once_with(self.ctx, 123, session=mock.sentinel.sess)
        self.assertEquals(self.resp.status, falcon.HTTP_200)

    def test_organizations_delete_404(self):
        od = self.patch('procession.db.api.organization_delete')
        gs = self.patch('procession.db.session.get_session')

        od.side_effect = exc.NotFound
        gs.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_delete, 123)

        od.assert_called_once_with(self.ctx, 123, session=mock.sentinel.sess)
        self.assertEquals(self.resp.status, falcon.HTTP_404)


class GroupsResourceTest(ResourceTestBase):

    def setUp(self):
        self.resource = resources.GroupsResource()
        super(GroupsResourceTest, self).setUp()

    def test_groups_get(self):
        with mock.patch('procession.api.search.SearchSpec') as ss:
            with mock.patch('procession.db.api.groups_get') as gg:
                ss.return_value = mock.sentinel.spec
                gg.return_value = fakes.FAKE_USERS

                self.as_auth(self.resource.on_get)

                gg.assert_called_with(self.ctx, mock.sentinel.spec)
                self.assertEquals(self.resp.status, falcon.HTTP_200)
                self.assertEquals(self.resp.body, fakes.FAKE_USERS)

    def test_groups_post(self):
        ds = self.patch('procession.api.helpers.deserialize')
        s = self.patch('procession.api.helpers.serialize')
        uc = self.patch('procession.db.api.group_create')
        gs = self.patch('procession.db.session.get_session')

        uc.return_value = fakes.FAKE_USER1
        ds.return_value = mock.sentinel.ds
        s.return_value = mock.sentinel.s
        gs.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_post)

        uc.assert_called_once_with(self.ctx, mock.sentinel.ds,
                                   session=mock.sentinel.sess)
        self.assertEquals(self.resp.status, falcon.HTTP_201)
        s.assert_called_once_with(self.req, fakes.FAKE_USER1)
        self.assertEquals(self.resp.body, mock.sentinel.s)

    def test_groups_post_400(self):
        ds = self.patch('procession.api.helpers.deserialize')
        s = self.patch('procession.api.helpers.serialize')
        uc = self.patch('procession.db.api.group_create')
        gs = self.patch('procession.db.session.get_session')

        uc.side_effect = ValueError
        ds.return_value = mock.sentinel.ds
        s.return_value = mock.sentinel.s
        gs.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_post)

        uc.assert_called_once_with(self.ctx, mock.sentinel.ds,
                                   session=mock.sentinel.sess)
        self.assertEquals(self.resp.status, falcon.HTTP_400)
        s.assert_not_called()
        self.assertThat(self.resp.body, matchers.Contains('Bad input'))


class GroupResourceTest(ResourceTestBase):

    def setUp(self):
        self.resource = resources.GroupResource()
        super(GroupResourceTest, self).setUp()

    def test_group_get(self):
        with mock.patch('procession.db.api.group_get_by_pk') as gg:
            gg.return_value = fakes.FAKE_USER1

            self.as_auth(self.resource.on_get, 123)

            gg.assert_called_with(self.ctx, 123)
            self.assertEquals(self.resp.status, falcon.HTTP_200)
            self.assertEquals(self.resp.body, fakes.FAKE_USER1)

            gg.reset()
            gg.side_effect = exc.NotFound()

            self.as_auth(self.resource.on_get, 123)

            gg.assert_called_with(self.ctx, 123)
            self.assertEquals(self.resp.status, falcon.HTTP_404)

    def test_group_get_404(self):
        with mock.patch('procession.db.api.group_get_by_pk') as gg:
            gg.side_effect = exc.NotFound()

            self.as_auth(self.resource.on_get, 123)

            gg.assert_called_with(self.ctx, 123)
            self.assertEquals(self.resp.status, falcon.HTTP_404)

    def test_groups_put(self):
        ds = self.patch('procession.api.helpers.deserialize')
        s = self.patch('procession.api.helpers.serialize')
        gu = self.patch('procession.db.api.group_update')
        gs = self.patch('procession.db.session.get_session')

        gu.return_value = fakes.FAKE_USER1
        ds.return_value = mock.sentinel.ds
        s.return_value = mock.sentinel.s
        gs.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_put, 123)

        gu.assert_called_once_with(self.ctx, 123, mock.sentinel.ds,
                                   session=mock.sentinel.sess)
        self.assertEquals(self.resp.status, falcon.HTTP_200)
        s.assert_called_once_with(self.req, fakes.FAKE_USER1)
        self.assertEquals(self.resp.body, mock.sentinel.s)

    def test_groups_put_404(self):
        ds = self.patch('procession.api.helpers.deserialize')
        s = self.patch('procession.api.helpers.serialize')
        gu = self.patch('procession.db.api.group_update')
        gs = self.patch('procession.db.session.get_session')

        gu.side_effect = exc.NotFound
        ds.return_value = mock.sentinel.ds
        s.return_value = mock.sentinel.s
        gs.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_put, 123)

        gu.assert_called_once_with(self.ctx, 123, mock.sentinel.ds,
                                   session=mock.sentinel.sess)
        self.assertEquals(self.resp.status, falcon.HTTP_404)
        s.assert_not_called()

    def test_groups_delete(self):
        gd = self.patch('procession.db.api.group_delete')
        gs = self.patch('procession.db.session.get_session')

        gd.return_value = fakes.FAKE_USER1
        gs.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_delete, 123)

        gd.assert_called_once_with(self.ctx, 123, session=mock.sentinel.sess)
        self.assertEquals(self.resp.status, falcon.HTTP_200)

    def test_groups_delete_404(self):
        gd = self.patch('procession.db.api.group_delete')
        gs = self.patch('procession.db.session.get_session')

        gd.side_effect = exc.NotFound
        gs.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_delete, 123)

        gd.assert_called_once_with(self.ctx, 123, session=mock.sentinel.sess)
        self.assertEquals(self.resp.status, falcon.HTTP_404)


class OrgGroupsResourceTest(ResourceTestBase):

    def setUp(self):
        self.resource = resources.OrgGroupsResource()
        super(OrgGroupsResourceTest, self).setUp()

    def test_org_groups_get(self):
        with mock.patch('procession.api.search.SearchSpec') as ss:
            with mock.patch('procession.db.api.groups_get') as gg:
                spec_mock = mock.MagicMock()
                ss.return_value = spec_mock
                gg.return_value = fakes.FAKE_USERS

                self.as_auth(self.resource.on_get, 123)

                spec_mock.filters.__setitem__.assert_called_once_with(
                    'root_organization_id', 123)
                gg.assert_called_with(self.ctx, spec_mock)
                self.assertEquals(self.resp.status, falcon.HTTP_200)
                self.assertEquals(self.resp.body, fakes.FAKE_USERS)

    def test_org_groups_post(self):
        ds = self.patch('procession.api.helpers.deserialize')
        s = self.patch('procession.api.helpers.serialize')
        uc = self.patch('procession.db.api.group_create')
        gs = self.patch('procession.db.session.get_session')

        add_mock = mock.MagicMock()

        uc.return_value = fakes.FAKE_USER1
        ds.return_value = add_mock
        s.return_value = mock.sentinel.s
        gs.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_post, 123)

        add_mock.__setitem__.assert_called_once_with(
            'root_organization_id', 123)
        uc.assert_called_once_with(self.ctx, add_mock,
                                   session=mock.sentinel.sess)
        self.assertEquals(self.resp.status, falcon.HTTP_201)
        s.assert_called_once_with(self.req, fakes.FAKE_USER1)
        self.assertEquals(self.resp.body, mock.sentinel.s)

    def test_groups_post_400(self):
        ds = self.patch('procession.api.helpers.deserialize')
        s = self.patch('procession.api.helpers.serialize')
        uc = self.patch('procession.db.api.group_create')
        gs = self.patch('procession.db.session.get_session')

        add_mock = mock.MagicMock()

        uc.side_effect = ValueError
        ds.return_value = add_mock
        s.return_value = mock.sentinel.s
        gs.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_post, 123)

        add_mock.__setitem__.assert_called_once_with(
            'root_organization_id', 123)
        uc.assert_called_once_with(self.ctx, add_mock,
                                   session=mock.sentinel.sess)
        self.assertEquals(self.resp.status, falcon.HTTP_400)
        s.assert_not_called()
        self.assertThat(self.resp.body, matchers.Contains('Bad input'))


class UsersResourceTest(ResourceTestBase):

    def setUp(self):
        self.resource = resources.UsersResource()
        super(UsersResourceTest, self).setUp()

    def test_users_get(self):
        with mock.patch('procession.api.search.SearchSpec') as ss:
            with mock.patch('procession.db.api.users_get') as ug:
                ss.return_value = mock.sentinel.spec
                ug.return_value = fakes.FAKE_USERS

                self.as_auth(self.resource.on_get)

                ug.assert_called_with(self.ctx, mock.sentinel.spec)
                self.assertEquals(self.resp.status, falcon.HTTP_200)
                self.assertEquals(self.resp.body, fakes.FAKE_USERS)

    def test_users_post(self):
        ds = self.patch('procession.api.helpers.deserialize')
        s = self.patch('procession.api.helpers.serialize')
        uc = self.patch('procession.db.api.user_create')
        gs = self.patch('procession.db.session.get_session')

        uc.return_value = fakes.FAKE_USER1
        ds.return_value = mock.sentinel.ds
        s.return_value = mock.sentinel.s
        gs.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_post)

        uc.assert_called_once_with(self.ctx, mock.sentinel.ds,
                                   session=mock.sentinel.sess)
        self.assertEquals(self.resp.status, falcon.HTTP_201)
        s.assert_called_once_with(self.req, fakes.FAKE_USER1)
        self.assertEquals(self.resp.body, mock.sentinel.s)

    def test_users_post_400(self):
        ds = self.patch('procession.api.helpers.deserialize')
        s = self.patch('procession.api.helpers.serialize')
        uc = self.patch('procession.db.api.user_create')
        gs = self.patch('procession.db.session.get_session')

        uc.side_effect = ValueError
        ds.return_value = mock.sentinel.ds
        s.return_value = mock.sentinel.s
        gs.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_post)

        uc.assert_called_once_with(self.ctx, mock.sentinel.ds,
                                   session=mock.sentinel.sess)
        self.assertEquals(self.resp.status, falcon.HTTP_400)
        s.assert_not_called()
        self.assertThat(self.resp.body, matchers.Contains('Bad input'))


class UserResourceTest(ResourceTestBase):

    def setUp(self):
        self.resource = resources.UserResource()
        super(UserResourceTest, self).setUp()

    def test_user_get(self):
        with mock.patch('procession.db.api.user_get_by_pk') as ug:
            ug.return_value = fakes.FAKE_USER1

            self.as_auth(self.resource.on_get, 123)

            ug.assert_called_with(self.ctx, 123)
            self.assertEquals(self.resp.status, falcon.HTTP_200)
            self.assertEquals(self.resp.body, fakes.FAKE_USER1)

            ug.reset()
            ug.side_effect = exc.NotFound()

            self.as_auth(self.resource.on_get, 123)

            ug.assert_called_with(self.ctx, 123)
            self.assertEquals(self.resp.status, falcon.HTTP_404)

    def test_user_get_404(self):
        with mock.patch('procession.db.api.user_get_by_pk') as ug:
            ug.side_effect = exc.NotFound()

            self.as_auth(self.resource.on_get, 123)

            ug.assert_called_with(self.ctx, 123)
            self.assertEquals(self.resp.status, falcon.HTTP_404)

    def test_users_put(self):
        ds = self.patch('procession.api.helpers.deserialize')
        s = self.patch('procession.api.helpers.serialize')
        uu = self.patch('procession.db.api.user_update')
        gs = self.patch('procession.db.session.get_session')

        uu.return_value = fakes.FAKE_USER1
        ds.return_value = mock.sentinel.ds
        s.return_value = mock.sentinel.s
        gs.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_put, 123)

        uu.assert_called_once_with(self.ctx, 123, mock.sentinel.ds,
                                   session=mock.sentinel.sess)
        self.assertEquals(self.resp.status, falcon.HTTP_200)
        s.assert_called_once_with(self.req, fakes.FAKE_USER1)
        self.assertEquals(self.resp.body, mock.sentinel.s)

    def test_users_put_404(self):
        ds = self.patch('procession.api.helpers.deserialize')
        s = self.patch('procession.api.helpers.serialize')
        uu = self.patch('procession.db.api.user_update')
        gs = self.patch('procession.db.session.get_session')

        uu.side_effect = exc.NotFound
        ds.return_value = mock.sentinel.ds
        s.return_value = mock.sentinel.s
        gs.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_put, 123)

        uu.assert_called_once_with(self.ctx, 123, mock.sentinel.ds,
                                   session=mock.sentinel.sess)
        self.assertEquals(self.resp.status, falcon.HTTP_404)
        s.assert_not_called()

    def test_users_delete(self):
        ud = self.patch('procession.db.api.user_delete')
        gs = self.patch('procession.db.session.get_session')

        ud.return_value = fakes.FAKE_USER1
        gs.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_delete, 123)

        ud.assert_called_once_with(self.ctx, 123, session=mock.sentinel.sess)
        self.assertEquals(self.resp.status, falcon.HTTP_200)

    def test_users_delete_404(self):
        ud = self.patch('procession.db.api.user_delete')
        gs = self.patch('procession.db.session.get_session')

        ud.side_effect = exc.NotFound
        gs.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_delete, 123)

        ud.assert_called_once_with(self.ctx, 123, session=mock.sentinel.sess)
        self.assertEquals(self.resp.status, falcon.HTTP_404)


class UserKeysResourceTest(ResourceTestBase):

    def setUp(self):
        self.resource = resources.UserKeysResource()
        super(UserKeysResourceTest, self).setUp()

    def test_user_keys_get(self):
        with mock.patch('procession.api.search.SearchSpec') as ss:
            with mock.patch('procession.db.api.user_keys_get') as ug:
                spec = mock.MagicMock()
                filters = mock.PropertyMock()
                type(spec).filters = filters
                ss.return_value = spec
                ug.return_value = mock.sentinel.keys

                self.as_auth(self.resource.on_get, 123)

                filters.assert_called_with()
                ug.assert_called_with(self.ctx, spec)
                self.assertEquals(self.resp.status, falcon.HTTP_200)
                self.assertEquals(self.resp.body, mock.sentinel.keys)

    def test_user_keys_post(self):
        ds = self.patch('procession.api.helpers.deserialize')
        s = self.patch('procession.api.helpers.serialize')
        uc = self.patch('procession.db.api.user_key_create')
        gs = self.patch('procession.db.session.get_session')

        key = mock.MagicMock()
        key.id = 567
        uc.return_value = key
        ds.return_value = mock.sentinel.ds
        s.return_value = mock.sentinel.s
        gs.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_post, 123)

        uc.assert_called_once_with(self.ctx, 123, mock.sentinel.ds,
                                   session=mock.sentinel.sess)
        self.assertEquals(self.resp.status, falcon.HTTP_201)
        s.assert_called_once_with(self.req, key)
        self.assertEquals(self.resp.body, mock.sentinel.s)
        self.assertEquals(self.resp.location, "/users/123/keys/567")

    def test_user_keys_post_400(self):
        ds = self.patch('procession.api.helpers.deserialize')
        s = self.patch('procession.api.helpers.serialize')
        uc = self.patch('procession.db.api.user_key_create')
        gs = self.patch('procession.db.session.get_session')

        key = mock.MagicMock()
        key.id = 567
        uc.side_effect = ValueError
        ds.return_value = mock.sentinel.ds
        s.return_value = mock.sentinel.s
        gs.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_post, 123)

        uc.assert_called_once_with(self.ctx, 123, mock.sentinel.ds,
                                   session=mock.sentinel.sess)
        self.assertEquals(self.resp.status, falcon.HTTP_400)
        s.assert_not_called()

    def test_user_keys_post_no_user_404(self):
        ds = self.patch('procession.api.helpers.deserialize')
        s = self.patch('procession.api.helpers.serialize')
        uc = self.patch('procession.db.api.user_key_create')
        gs = self.patch('procession.db.session.get_session')

        key = mock.MagicMock()
        key.id = 567
        uc.side_effect = exc.NotFound
        ds.return_value = mock.sentinel.ds
        s.return_value = mock.sentinel.s
        gs.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_post, 123)

        uc.assert_called_once_with(self.ctx, 123, mock.sentinel.ds,
                                   session=mock.sentinel.sess)
        self.assertEquals(self.resp.status, falcon.HTTP_404)
        s.assert_not_called()


class UserKeyResourceTest(ResourceTestBase):

    def setUp(self):
        self.resource = resources.UserKeyResource()
        super(UserKeyResourceTest, self).setUp()

    def test_user_key_get(self):
        with mock.patch('procession.db.api.user_key_get_by_pk') as uk:
            uk.return_value = fakes.FAKE_KEY1

            self.as_auth(self.resource.on_get, 123, 'ABC')

            uk.assert_called_with(self.ctx, 123, 'ABC')
            self.assertEquals(self.resp.status, falcon.HTTP_200)
            self.assertEquals(self.resp.body, fakes.FAKE_KEY1)

            uk.reset()
            uk.side_effect = exc.NotFound()

            self.as_auth(self.resource.on_get, 123, 'ABC')

            uk.assert_called_with(self.ctx, 123, 'ABC')
            self.assertEquals(self.resp.status, falcon.HTTP_404)

    def test_user_key_get_404(self):
        with mock.patch('procession.db.api.user_key_get_by_pk') as uk:
            uk.side_effect = exc.NotFound()

            self.as_auth(self.resource.on_get, 123, 'ABC')

            uk.assert_called_with(self.ctx, 123, 'ABC')
            self.assertEquals(self.resp.status, falcon.HTTP_404)

    def test_user_key_delete(self):
        uk = self.patch('procession.db.api.user_key_delete')
        gs = self.patch('procession.db.session.get_session')

        uk.return_value = fakes.FAKE_USER1
        gs.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_delete, 123, 'ABC')

        uk.assert_called_once_with(self.ctx, 123, 'ABC',
                                   session=mock.sentinel.sess)
        self.assertEquals(self.resp.status, falcon.HTTP_200)

    def test_users_delete_404(self):
        uk = self.patch('procession.db.api.user_key_delete')
        gs = self.patch('procession.db.session.get_session')

        uk.side_effect = exc.NotFound
        gs.return_value = mock.sentinel.sess

        self.as_auth(self.resource.on_delete, 123, 'ABC')

        uk.assert_called_once_with(self.ctx, 123, 'ABC',
                                   session=mock.sentinel.sess)
        self.assertEquals(self.resp.status, falcon.HTTP_404)
