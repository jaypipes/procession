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
from procession.rest.resources import group

from tests.rest.resources import base


class GroupsResourceTest(base.ResourceTestCase):

    def setUp(self):
        super(GroupsResourceTest, self).setUp()
        self.resource = group.GroupsResource(self.conf)

    @mock.patch('procession.objects.Group.get_many')
    @mock.patch('procession.search.SearchSpec.from_http_req')
    def test_get_200(self, ss, get):
        ss.return_value = mock.sentinel.ss
        get.return_value = mock.sentinel.get

        self.as_auth(self.resource.on_get)

        get.assert_called_once_with(mock.sentinel.ss)
        self.assertEquals(self.resp.status, falcon.HTTP_200)
        self.assertEquals(self.resp.body, mock.sentinel.get)

    @mock.patch('procession.objects.Group.from_http_req')
    def test_post_201(self, fhr):
        obj_mock = mock.MagicMock()
        fhr.return_value = obj_mock

        self.as_auth(self.resource.on_post)

        fhr.assert_called_once_with(self.req)
        obj_mock.save.assert_called_once_with()
        self.assertEquals(self.resp.status, falcon.HTTP_201)
        self.assertEquals(self.resp.body, obj_mock)

    @mock.patch('procession.objects.Group.from_http_req')
    def test_post_400(self, fhr):
        fhr.side_effect = exc.BadInput

        self.as_auth(self.resource.on_post)

        self.assertEquals(self.resp.status, falcon.HTTP_400)
        self.assertThat(self.resp.body, matchers.Contains('Bad input'))


class GroupResourceTest(base.ResourceTestCase):

    def setUp(self):
        super(GroupResourceTest, self).setUp()
        self.resource = group.GroupResource(self.conf)

    @mock.patch('procession.objects.Group.get_by_slug_or_key')
    def test_get_200(self, get):
        get.return_value = mock.sentinel.get

        self.as_auth(self.resource.on_get, 123)

        get.assert_called_once_with(self.req, 123)
        self.assertEquals(self.resp.status, falcon.HTTP_200)
        self.assertEquals(self.resp.body, mock.sentinel.get)

    @mock.patch('procession.objects.Group.get_by_slug_or_key')
    def test_get_404(self, get):
        get.side_effect = exc.NotFound

        self.as_auth(self.resource.on_get, 123)

        get.assert_called_once_with(self.req, 123)
        self.assertEquals(self.resp.status, falcon.HTTP_404)

    @mock.patch('procession.objects.Group.from_http_req')
    def test_put_200(self, fhr):
        obj_mock = mock.MagicMock()
        fhr.return_value = obj_mock

        self.as_auth(self.resource.on_put, 123)

        fhr.assert_called_once_with(self.req)
        obj_mock.update.assert_called_once_with()
        self.assertEquals(self.resp.status, falcon.HTTP_200)
        self.assertEquals(self.resp.body, obj_mock)

    @mock.patch('procession.objects.Group.from_http_req')
    def test_put_400(self, fhr):
        fhr.side_effect = exc.BadInput

        self.as_auth(self.resource.on_put, 123)

        fhr.assert_called_once_with(self.req)
        self.assertEquals(self.resp.status, falcon.HTTP_400)
        self.assertThat(self.resp.body, matchers.Contains('Bad input'))

    @mock.patch('procession.objects.Group.from_http_req')
    def test_put_404(self, fhr):
        obj_mock = mock.MagicMock()
        obj_mock.update.side_effect = exc.NotFound
        fhr.return_value = obj_mock

        self.as_auth(self.resource.on_put, 123)

        fhr.assert_called_once_with(self.req)
        obj_mock.update.assert_called_once_with()
        self.assertEquals(self.resp.status, falcon.HTTP_404)

    @mock.patch('procession.objects.Group.get_by_slug_or_key')
    def test_delete_204(self, get):
        obj_mock = mock.MagicMock()
        get.return_value = obj_mock

        self.as_auth(self.resource.on_delete, 123)

        get.assert_called_once_with(self.req, 123)
        obj_mock.remove.assert_called_once_with()
        self.assertEquals(self.resp.status, falcon.HTTP_204)

    @mock.patch('procession.objects.Group.get_by_slug_or_key')
    def test_delete_404(self, get):
        get.side_effect = exc.NotFound

        self.as_auth(self.resource.on_delete, 123)

        get.assert_called_once_with(self.req, 123)
        self.assertEquals(self.resp.status, falcon.HTTP_404)


class GroupUsersResourceTest(base.ResourceTestCase):

    def setUp(self):
        super(GroupUsersResourceTest, self).setUp()
        self.resource = group.GroupUsersResource(self.conf)

    @mock.patch('procession.objects.Group.get_users')
    @mock.patch('procession.search.SearchSpec.from_http_req')
    def test_get_200(self, ss, get):
        ss_mock = mock.MagicMock()
        ss.return_value = ss_mock
        get.return_value = mock.sentinel.get

        self.as_auth(self.resource.on_get, 123)
        ss_mock.filter_by.assert_called_once_with(groupId=123)
        get.assert_called_once_with(ss_mock)
        self.assertEquals(self.resp.status, falcon.HTTP_200)
        self.assertEquals(self.resp.body, mock.sentinel.get)

    @mock.patch('procession.objects.Group.get_users')
    @mock.patch('procession.search.SearchSpec.from_http_req')
    def test_get_404(self, ss, get):
        ss_mock = mock.MagicMock()
        ss.return_value = ss_mock
        get.side_effect = exc.NotFound

        self.as_auth(self.resource.on_get, 123)

        get.assert_called_once_with(ss_mock)
        self.assertEquals(self.resp.status, falcon.HTTP_404)
