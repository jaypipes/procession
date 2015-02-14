# -*- encoding: utf-8 -*-
#
# Copyright 2015 Jay Pipes
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

import mock
import testtools

from sqlalchemy.orm import exc as sao_exc

from procession import exc
from procession.storage.sql import api

from tests import base


class TestGetMany(base.UnitTest):

    def setUp(self):
        super(TestGetMany, self).setUp()
        self.sess = mock.MagicMock()
        # Mocks representing the SQLAlchemy query object returned from various
        # calls on the query object itself. The methods on the query object,
        # such as limit(), and order_by() all return the query object itself,
        # allowing call chaining.
        query_mock = mock.MagicMock()
        query_mock.order_by.return_value = query_mock
        query_mock.limit.return_value = query_mock
        query_mock.filter_by.return_value = query_mock
        self.sess.query.return_value = query_mock
        self.query = query_mock

    def test_no_filters_no_order_no_marker(self):
        model_mock = mock.MagicMock()
        model_mock.get_default_order_by.return_value = [
            mock.sentinel.def_order
        ]
        search_mock = mock.MagicMock(filters=None,
                                     marker=None,
                                     limit=mock.sentinel.limit)
        search_mock.get_order_by.return_value = None

        res = api.get_many(self.sess, model_mock, search_mock)

        model_mock.get_default_order_by.assert_called_once_with()
        search_mock.get_order_by.assert_called_once_with()
        self.sess.query.assert_called_once_with(model_mock)
        self.assertFalse(self.query.filter_by.called)
        self.query.limit.assert_called_once_with(mock.sentinel.limit)
        self.query.order_by.assert_called_once_with(mock.sentinel.def_order)
        self.query.all.assert_called_once_with()
        self.assertEqual(self.query.all.return_value, res)

    def test_order_no_marker(self):
        model_mock = mock.MagicMock()
        search_mock = mock.MagicMock(filters=None,
                                     marker=None,
                                     limit=mock.sentinel.limit)
        search_mock.get_order_by.return_value = [
            mock.sentinel.spec_order
        ]

        api.get_many(self.sess, model_mock, search_mock)

        self.assertFalse(model_mock.get_default_order_by.called)
        search_mock.get_order_by.assert_called_once_with()
        self.query.order_by.assert_called_once_with(mock.sentinel.spec_order)

    @mock.patch.object(api, '_paginate_query')
    def test_order_with_marker(self, paginate_mock):
        model_mock = mock.MagicMock()
        search_mock = mock.MagicMock(filters=None,
                                     marker=mock.sentinel.marker,
                                     limit=mock.sentinel.limit)
        search_mock.get_order_by.return_value = [
            mock.sentinel.spec_order
        ]

        api.get_many(self.sess, model_mock, search_mock)

        self.assertFalse(model_mock.get_default_order_by.called)
        search_mock.get_order_by.assert_called_once_with()

        self.assertFalse(self.query.order_by.called)
        paginate_mock.assert_called_once_with(self.sess,
                                              self.query,
                                              model_mock,
                                              mock.sentinel.marker,
                                              [mock.sentinel.spec_order])

    def test_filter_by(self):
        model_mock = mock.MagicMock()
        model_mock.get_default_order_by.return_value = [
            mock.sentinel.def_order
        ]
        filters = {
            'field': mock.sentinel.field
        }
        search_mock = mock.MagicMock(filters=filters,
                                     marker=None,
                                     limit=mock.sentinel.limit)
        search_mock.get_order_by.return_value = None

        api.get_many(self.sess, model_mock, search_mock)

        self.query.filter_by.assert_called_once_with(field=mock.sentinel.field)


class TestGetOne(base.UnitTest):

    def setUp(self):
        super(TestGetOne, self).setUp()
        self.sess = mock.MagicMock()
        # Mocks representing the SQLAlchemy query object returned from various
        # calls on the query object itself. The methods on the query object,
        # such as limit(), and order_by() all return the query object itself,
        # allowing call chaining.
        query_mock = mock.MagicMock()
        query_mock.filter_by.return_value = query_mock
        self.sess.query.return_value = query_mock
        self.query = query_mock

    def test_success(self):
        res = api.get_one(self.sess, mock.sentinel.model,
                          field=mock.sentinel.field)
        self.sess.query.assert_called_once_with(mock.sentinel.model)
        self.query.filter_by.assert_called_once_with(field=mock.sentinel.field)
        self.assertEqual(self.query.one.return_value, res)

    def test_not_found(self):
        self.query.one.side_effect = sao_exc.NoResultFound
        with testtools.ExpectedException(exc.NotFound):
            api.get_one(self.sess, mock.sentinel.model,
                        field=mock.sentinel.field)
        self.sess.query.assert_called_once_with(mock.sentinel.model)
        self.query.filter_by.assert_called_once_with(field=mock.sentinel.field)
