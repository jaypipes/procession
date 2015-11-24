# -*- encoding: utf-8 -*-
#
# Copyright 2013-2014 Jay Pipes
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

import falcon
import mock
from testtools import matchers

from procession import exc
from procession.rest.resources import user

from tests.rest.resources import base


class UsersResourceTest(base.ResourceTestCase):

    def setUp(self):
        super(UsersResourceTest, self).setUp()
        self.resource = user.UsersResource(self.conf)

    @mock.patch('procession.objects.User.get_many')
    @mock.patch('procession.search.SearchSpec.from_http_req')
    def test_get_200(self, ss, get):
        ss.return_value = mock.sentinel.ss
        get.return_value = mock.sentinel.get

        self.as_auth(self.resource.on_get)

        get.assert_called_once_with(mock.sentinel.ss)
        self.assertEquals(self.resp.status, falcon.HTTP_200)
        self.assertEquals(self.resp.body, mock.sentinel.get)

    @mock.patch('procession.objects.User.from_http_req')
    def test_post_201(self, fhr):
        obj_mock = mock.MagicMock()
        fhr.return_value = obj_mock

        self.as_auth(self.resource.on_post)

        fhr.assert_called_once_with(self.req)
        obj_mock.save.assert_called_once_with()
        self.assertEquals(self.resp.status, falcon.HTTP_201)
        self.assertEquals(self.resp.body, obj_mock)

    @mock.patch('procession.objects.User.from_http_req')
    def test_post_400(self, fhr):
        fhr.side_effect = exc.BadInput

        self.as_auth(self.resource.on_post)

        self.assertEquals(self.resp.status, falcon.HTTP_400)
        self.assertThat(self.resp.body, matchers.Contains('Bad input'))


class UserResourceTest(base.ResourceTestCase):

    def setUp(self):
        super(UserResourceTest, self).setUp()
        self.resource = user.UserResource(self.conf)

    @mock.patch('procession.objects.User.get_by_slug_or_key')
    def test_get_200(self, get):
        get.return_value = mock.sentinel.get

        self.as_auth(self.resource.on_get, 123)

        get.assert_called_once_with(self.req, 123)
        self.assertEquals(self.resp.status, falcon.HTTP_200)
        self.assertEquals(self.resp.body, mock.sentinel.get)

    @mock.patch('procession.objects.User.get_by_slug_or_key')
    def test_get_404(self, get):
        get.side_effect = exc.NotFound

        self.as_auth(self.resource.on_get, 123)

        get.assert_called_once_with(self.req, 123)
        self.assertEquals(self.resp.status, falcon.HTTP_404)

    @mock.patch('procession.objects.User.from_http_req')
    def test_put_200(self, fhr):
        obj_mock = mock.MagicMock()
        fhr.return_value = obj_mock

        self.as_auth(self.resource.on_put, 123)

        fhr.assert_called_once_with(self.req)
        obj_mock.update.assert_called_once_with()
        self.assertEquals(self.resp.status, falcon.HTTP_200)
        self.assertEquals(self.resp.body, obj_mock)

    @mock.patch('procession.objects.User.from_http_req')
    def test_put_400(self, fhr):
        fhr.side_effect = exc.BadInput

        self.as_auth(self.resource.on_put, 123)

        fhr.assert_called_once_with(self.req)
        self.assertEquals(self.resp.status, falcon.HTTP_400)
        self.assertThat(self.resp.body, matchers.Contains('Bad input'))

    @mock.patch('procession.objects.User.from_http_req')
    def test_put_404(self, fhr):
        obj_mock = mock.MagicMock()
        obj_mock.update.side_effect = exc.NotFound
        fhr.return_value = obj_mock

        self.as_auth(self.resource.on_put, 123)

        fhr.assert_called_once_with(self.req)
        obj_mock.update.assert_called_once_with()
        self.assertEquals(self.resp.status, falcon.HTTP_404)

    @mock.patch('procession.objects.User.get_by_slug_or_key')
    def test_delete_204(self, get):
        obj_mock = mock.MagicMock()
        get.return_value = obj_mock

        self.as_auth(self.resource.on_delete, 123)

        get.assert_called_once_with(self.req, 123)
        obj_mock.remove.assert_called_once_with()
        self.assertEquals(self.resp.status, falcon.HTTP_204)

    @mock.patch('procession.objects.User.get_by_slug_or_key')
    def test_delete_404(self, get):
        get.side_effect = exc.NotFound

        self.as_auth(self.resource.on_delete, 123)

        get.assert_called_once_with(self.req, 123)
        self.assertEquals(self.resp.status, falcon.HTTP_404)


class UserKeysResourceTest(base.ResourceTestCase):

    def setUp(self):
        super(UserKeysResourceTest, self).setUp()
        self.resource = user.UserKeysResource(self.conf)

    @mock.patch('procession.objects.User.get_by_slug_or_key')
    def test_get_200(self, get):
        obj_mock = mock.MagicMock()
        obj_mock.get_public_keys.return_value = mock.sentinel.get
        get.return_value = obj_mock

        self.as_auth(self.resource.on_get, 123)

        get.assert_called_once_with(self.req, 123)
        obj_mock.get_public_keys.assert_called_once_with()
        self.assertEquals(self.resp.status, falcon.HTTP_200)
        self.assertEquals(self.resp.body, mock.sentinel.get)

    @mock.patch('procession.objects.User.get_by_slug_or_key')
    def test_get_404(self, get):
        get.side_effect = exc.NotFound

        self.as_auth(self.resource.on_get, 123)

        get.assert_called_once_with(self.req, 123)
        self.assertEquals(self.resp.status, falcon.HTTP_404)

    @mock.patch('procession.objects.UserPublicKey.from_http_req')
    @mock.patch('procession.objects.User.get_by_slug_or_key')
    def test_post_201(self, get, fhr):
        user_mock = mock.MagicMock(id=mock.sentinel.user_id)
        get.return_value = user_mock
        obj_mock = mock.MagicMock()
        fhr.return_value = obj_mock

        self.as_auth(self.resource.on_post, 123)

        get.assert_called_once_with(self.req, 123)
        fhr.assert_called_once_with(self.req, userId=mock.sentinel.user_id)
        obj_mock.save.assert_called_once_with()
        self.assertEquals(self.resp.status, falcon.HTTP_201)
        self.assertEquals(self.resp.body, obj_mock)

    @mock.patch('procession.objects.UserPublicKey.from_http_req')
    @mock.patch('procession.objects.User.get_by_slug_or_key')
    def test_post_404(self, get, fhr):
        get.side_effect = exc.NotFound

        self.as_auth(self.resource.on_post, 123)

        get.assert_called_once_with(self.req, 123)
        self.assertFalse(fhr.called)
        self.assertEquals(self.resp.status, falcon.HTTP_404)

    @mock.patch('procession.objects.UserPublicKey.from_http_req')
    @mock.patch('procession.objects.User.get_by_slug_or_key')
    def test_post_400(self, get, fhr):
        user_mock = mock.MagicMock(id=mock.sentinel.user_id)
        get.return_value = user_mock
        fhr.side_effect = exc.BadInput

        self.as_auth(self.resource.on_post, 123)

        get.assert_called_once_with(self.req, 123)
        fhr.assert_called_once_with(self.req, userId=mock.sentinel.user_id)
        self.assertEquals(self.resp.status, falcon.HTTP_400)
        self.assertThat(self.resp.body, matchers.Contains('Bad input'))


class UserKeyResourceTest(base.ResourceTestCase):

    def setUp(self):
        super(UserKeyResourceTest, self).setUp()
        self.resource = user.UserKeyResource(self.conf)

    @mock.patch('procession.objects.UserPublicKey.get_one')
    @mock.patch('procession.search.SearchSpec.from_http_req')
    @mock.patch('procession.objects.User.get_by_slug_or_key')
    def test_get_200(self, uget, ss, get):
        user_mock = mock.MagicMock(id=mock.sentinel.user_id)
        uget.return_value = user_mock
        ss_mock = mock.MagicMock()
        ss.return_value = ss_mock
        get.return_value = mock.sentinel.get

        self.as_auth(self.resource.on_get, 123, 'ABC')

        ss_mock.filter_by.assert_called_once_with(userId=mock.sentinel.user_id,
                                                  fingerprint='ABC')
        uget.assert_called_once_with(self.req, 123)
        get.assert_called_once_with(ss_mock)
        self.assertEquals(self.resp.status, falcon.HTTP_200)
        self.assertEquals(self.resp.body, mock.sentinel.get)

    @mock.patch('procession.objects.UserPublicKey.get_one')
    @mock.patch('procession.search.SearchSpec.from_http_req')
    @mock.patch('procession.objects.User.get_by_slug_or_key')
    def test_get_404_user(self, uget, ss, get):
        uget.side_effect = exc.NotFound

        self.as_auth(self.resource.on_get, 123, 'ABC')

        uget.assert_called_once_with(self.req, 123)
        self.assertFalse(ss.called)
        self.assertFalse(get.called)
        self.assertEquals(self.resp.status, falcon.HTTP_404)

    @mock.patch('procession.objects.UserPublicKey.get_one')
    @mock.patch('procession.search.SearchSpec.from_http_req')
    @mock.patch('procession.objects.User.get_by_slug_or_key')
    def test_get_404_key(self, uget, ss, get):
        user_mock = mock.MagicMock(id=mock.sentinel.user_id)
        uget.return_value = user_mock
        get.side_effect = exc.NotFound
        ss_mock = mock.MagicMock()
        ss.return_value = ss_mock

        self.as_auth(self.resource.on_get, 123, 'ABC')

        ss_mock.filter_by.assert_called_once_with(userId=mock.sentinel.user_id,
                                                  fingerprint='ABC')
        get.assert_called_once_with(ss_mock)
        self.assertEquals(self.resp.status, falcon.HTTP_404)

    @mock.patch('procession.objects.UserPublicKey.get_one')
    @mock.patch('procession.search.SearchSpec.from_http_req')
    @mock.patch('procession.objects.User.get_by_slug_or_key')
    def test_delete_204(self, uget, ss, get):
        user_mock = mock.MagicMock(id=mock.sentinel.user_id)
        uget.return_value = user_mock
        obj_mock = mock.MagicMock()
        get.return_value = obj_mock
        ss_mock = mock.MagicMock()
        ss.return_value = ss_mock

        self.as_auth(self.resource.on_delete, 123, 'ABC')

        ss_mock.filter_by.assert_called_once_with(userId=mock.sentinel.user_id,
                                                  fingerprint='ABC')
        get.assert_called_once_with(ss_mock)
        obj_mock.remove.assert_called_once_with()
        self.assertEquals(self.resp.status, falcon.HTTP_204)

    @mock.patch('procession.objects.UserPublicKey.get_one')
    @mock.patch('procession.search.SearchSpec.from_http_req')
    @mock.patch('procession.objects.User.get_by_slug_or_key')
    def test_delete_404_user(self, uget, ss, get):
        uget.side_effect = exc.NotFound

        self.as_auth(self.resource.on_delete, 123, 'ABC')

        uget.assert_called_once_with(self.req, 123)
        self.assertFalse(ss.called)
        self.assertFalse(get.called)
        self.assertEquals(self.resp.status, falcon.HTTP_404)

    @mock.patch('procession.objects.UserPublicKey.get_one')
    @mock.patch('procession.search.SearchSpec.from_http_req')
    @mock.patch('procession.objects.User.get_by_slug_or_key')
    def test_delete_404_key(self, uget, ss, get):
        user_mock = mock.MagicMock(id=mock.sentinel.user_id)
        uget.return_value = user_mock
        get.side_effect = exc.NotFound
        ss_mock = mock.MagicMock()
        ss.return_value = ss_mock

        self.as_auth(self.resource.on_delete, 123, 'ABC')

        ss_mock.filter_by.assert_called_once_with(userId=mock.sentinel.user_id,
                                                  fingerprint='ABC')
        get.assert_called_once_with(ss_mock)
        self.assertEquals(self.resp.status, falcon.HTTP_404)


class UserGroupsResourceTest(base.ResourceTestCase):

    def setUp(self):
        super(UserGroupsResourceTest, self).setUp()
        self.resource = user.UserGroupsResource(self.conf)

    @mock.patch('procession.objects.User.get_by_slug_or_key')
    def test_get_200(self, get):
        user_mock = mock.MagicMock(id=mock.sentinel.user_id)
        user_mock.get_groups.return_value = mock.sentinel.get
        get.return_value = user_mock

        self.as_auth(self.resource.on_get, 123)

        get.assert_called_once_with(self.req, 123)
        user_mock.get_groups.assert_called_once_with()
        self.assertEquals(self.resp.status, falcon.HTTP_200)
        self.assertEquals(self.resp.body, mock.sentinel.get)

    @mock.patch('procession.objects.User.get_by_slug_or_key')
    def test_get_404(self, get):
        get.side_effect = exc.NotFound

        self.as_auth(self.resource.on_get, 123)

        get.assert_called_once_with(self.req, 123)
        self.assertEquals(self.resp.status, falcon.HTTP_404)


class UserGroupResourceTest(base.ResourceTestCase):

    def setUp(self):
        super(UserGroupResourceTest, self).setUp()
        self.resource = user.UserGroupResource(self.conf)

    @mock.patch('procession.objects.User.get_by_slug_or_key')
    def test_delete_204(self, get):
        obj_mock = mock.MagicMock()
        get.return_value = obj_mock

        self.as_auth(self.resource.on_delete, 123, 'ABC')

        get.assert_called_once_with(self.req, 123)
        obj_mock.remove_from_group.assert_called_once_with('ABC')
        self.assertEquals(self.resp.status, falcon.HTTP_204)

    @mock.patch('procession.objects.User.get_by_slug_or_key')
    def test_delete_404_user(self, get):
        get.side_effect = exc.NotFound

        self.as_auth(self.resource.on_delete, 123, 'ABC')

        get.assert_called_once_with(self.req, 123)
        self.assertEquals(self.resp.status, falcon.HTTP_404)

    @mock.patch('procession.objects.User.get_by_slug_or_key')
    def test_delete_404_group(self, get):
        obj_mock = mock.MagicMock()
        obj_mock.remove_from_group.side_effect = exc.NotFound
        get.return_value = obj_mock

        self.as_auth(self.resource.on_delete, 123, 'ABC')

        get.assert_called_once_with(self.req, 123)
        self.assertEquals(self.resp.status, falcon.HTTP_404)

    @mock.patch('procession.objects.User.get_by_slug_or_key')
    def test_put_204(self, get):
        obj_mock = mock.MagicMock()
        get.return_value = obj_mock

        self.as_auth(self.resource.on_put, 123, 'ABC')

        get.assert_called_once_with(self.req, 123)
        obj_mock.add_to_group.assert_called_once_with('ABC')
        self.assertEquals(self.resp.status, falcon.HTTP_204)

    @mock.patch('procession.objects.User.get_by_slug_or_key')
    def test_put_404_user(self, get):
        get.side_effect = exc.NotFound

        self.as_auth(self.resource.on_put, 123, 'ABC')

        get.assert_called_once_with(self.req, 123)
        self.assertEquals(self.resp.status, falcon.HTTP_404)

    @mock.patch('procession.objects.User.get_by_slug_or_key')
    def test_put_404_group(self, get):
        obj_mock = mock.MagicMock()
        obj_mock.add_to_group.side_effect = exc.NotFound
        get.return_value = obj_mock

        self.as_auth(self.resource.on_put, 123, 'ABC')

        get.assert_called_once_with(self.req, 123)
        self.assertEquals(self.resp.status, falcon.HTTP_404)
