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

import mock
import testtools
from testtools import matchers

from procession import exc
from procession.db import api
from procession.db import session

from tests import base
from tests import fakes


class TestDbApi(base.UnitTest):

    # Note that this particular unit test is more than just a unit test. It
    # is partly a functional test of the DB API layer as well, since mocking
    # out all of SQLAlchemy was not particularly nice, nor all that useful
    # in identifying bugs. So, these tests do actually execute the various
    # database queries against an SQLite database backend and verify things
    # like transaction safety.

    def setUp(self):
        super(TestDbApi, self).setUp()
        self.sess = session.get_session()

    def test_user_create_bad_data(self):
        ctx = mock.Mock()
        user_info = {}
        with testtools.ExpectedException(ValueError):
            api.user_create(ctx, user_info)

    def test_user_update_bad_data(self):
        ctx = mock.Mock()
        user_info = {
            'display_name': 'foo',
            'email': 'foo@example.com'
        }
        u = api.user_create(ctx, user_info, session=self.sess)
        self.assertIsNotNone(u.id)
        self.addCleanup(api.user_delete, ctx, u.id, session=self.sess)

        update_info = {
            'display_name': None
        }
        with testtools.ExpectedException(ValueError):
            api.user_update(ctx, u.id, update_info, session=self.sess)

    def test_user_delete_bad_input(self):
        ctx = mock.Mock()
        user_id = 'nonexisting'
        with testtools.ExpectedException(exc.BadInput):
            api.user_delete(ctx, user_id, session=self.sess)

    def test_user_update_bad_input(self):
        ctx = mock.Mock()
        user_id = 'nonexisting'
        with testtools.ExpectedException(exc.BadInput):
            api.user_update(ctx, user_id, {}, session=self.sess)

    def test_user_delete_not_found(self):
        ctx = mock.Mock()
        with testtools.ExpectedException(exc.NotFound):
            api.user_delete(ctx, fakes.FAKE_UUID1, session=self.sess)

    def test_user_update_not_found(self):
        ctx = mock.Mock()
        with testtools.ExpectedException(exc.NotFound):
            api.user_update(ctx, fakes.FAKE_UUID1, {}, session=self.sess)

    def test_user_create_invalid_attr(self):
        ctx = mock.Mock()
        user_info = {
            'display_name': 'foo',
            'email': 'foo@example.com',
            'nonexistingattr': True
        }
        with testtools.ExpectedException(TypeError):
            api.user_create(ctx, user_info, session=self.sess)

    def test_user_crud(self):
        ctx = mock.Mock()
        user_info = {
            'display_name': 'foo',
            'email': 'foo@example.com'
        }
        u = api.user_create(ctx, user_info, session=self.sess)
        self.assertIsNotNone(u.id)

        with testtools.ExpectedException(exc.Duplicate):
            u = api.user_create(ctx, user_info, session=self.sess)

        self.assertEquals(u.display_name, user_info['display_name'])

        update_info = {
            'display_name': 'bar'
        }
        u = api.user_update(ctx, u.id, update_info, session=self.sess)
        self.assertEquals('bar', u.display_name)
        # Verify that the session was not committed since we did not
        # specify a commit kwarg
        self.assertTrue(self.sess.dirty)
        # Now do the same thing and verify the session was committed
        u = api.user_update(ctx, u.id, update_info, session=self.sess,
                            commit=True)
        self.assertFalse(self.sess.dirty)

        # Test an invalid attribute set
        update_info = {
            'nonexistingattr': True
        }
        with testtools.ExpectedException(exc.BadInput):
            api.user_update(ctx, u.id, update_info, session=self.sess)

        # Now we test valid addition of public SSH keys to the
        # new user object.
        key_info = {'fingerprint': '1234',
                    'public_key': 'blah'}
        k = api.user_key_create(ctx, u.id, key_info, commit=True)
        self.assertEquals(k.fingerprint, key_info['fingerprint'])

        spec = fakes.get_search_spec(filters=dict(user_id=u.id))
        keys = api.user_keys_get(ctx, spec)
        self.assertThat(keys, matchers.HasLength(1))
        self.assertThat(keys, matchers.Contains(k))

        # Try to add a new key with same fingerprint
        with testtools.ExpectedException(exc.Duplicate):
            api.user_key_create(ctx, u.id, key_info)

        api.user_delete(ctx, u.id, session=self.sess)

        with testtools.ExpectedException(exc.NotFound):
            api.user_delete(ctx, u.id, session=self.sess)

        keys = api.user_keys_get(ctx, spec)
        self.assertThat(keys, matchers.HasLength(0))

    def test_user_get_by_id_not_found(self):
        ctx = mock.Mock()
        with testtools.ExpectedException(exc.NotFound):
            api.user_get_by_id(ctx, fakes.FAKE_UUID1, session=self.sess)

    def test_users_get(self):
        ctx = mock.Mock()
        user_infos = [
            {
                'display_name': 'foo',
                'email': 'foo@example.com'
            },
            {
                'display_name': 'bar',
                'email': 'bar@example.com'
            },
            {
                'display_name': 'baz',
                'email': 'baz@example.com'
            },
        ]
        # The IDs of the users, indexed by email...
        user_ids = {}
        for user_info in user_infos:
            u = api.user_create(ctx, user_info, session=self.sess)
            self.assertIsNotNone(u.id)
            self.addCleanup(api.user_delete, ctx, u.id, session=self.sess)
            user_ids[user_info['email']] = u.id

        # Empty fake search spec has a limit of 2, so test
        # that with an empty spec, we get 2 records, and that
        # they are the last two records created since the
        # default sort order on the User model is created_at desc.
        spec = fakes.get_search_spec()
        users = api.users_get(ctx, spec, session=self.sess)
        self.assertThat(users, matchers.HasLength(2))
        user_names = [u.display_name for u in users]
        self.assertThat(user_names, matchers.Not(matchers.Contains('foo')))

        # Now test the same thing, only override the ordering to order
        # over the email address.
        spec = fakes.get_search_spec(order_by=["email desc"])
        users = api.users_get(ctx, spec, session=self.sess)
        self.assertThat(users, matchers.HasLength(2))
        user_names = [u.display_name for u in users]
        self.assertThat(user_names, matchers.Not(matchers.Contains('bar')))

        # Test a simple filter on unique email address returns
        # just one user, with the correct email.
        spec = fakes.get_search_spec(filters=dict(email='bar@example.com'))
        users = api.users_get(ctx, spec, session=self.sess)
        self.assertThat(users, matchers.HasLength(1))
        self.assertEquals(users[0].email, 'bar@example.com')

        # Test pagination results for sorting by desc email, with
        # a marker of the baz user's ID, which should cause the
        # results to be the second "page" of results with only a single
        # record in the page -- that of the bar user. This tests the
        # short-circuit of supplying an already-unique sort key

        spec = fakes.get_search_spec(order_by=["email desc"],
                                     marker=user_ids['baz@example.com'])
        users = api.users_get(ctx, spec, session=self.sess)
        self.assertThat(users, matchers.HasLength(1))
        self.assertEquals(users[0].email, 'bar@example.com')

        # Test pagination results for sorting by asc created_on, with
        # a marker of the bar user. This tests the scenario in pagination
        # where we must add an additional sort on a unique column when
        # the user has not supplied a unique sort order.
        spec = fakes.get_search_spec(order_by=["created_on asc"],
                                     marker=user_ids['bar@example.com'])
        users = api.users_get(ctx, spec, session=self.sess)
        self.assertThat(users, matchers.HasLength(1))
        self.assertEquals(users[0].email, 'baz@example.com')

        # Verify that supplying a marker that doesn't exist in the
        # database raises a BadInput.
        with testtools.ExpectedException(exc.BadInput):
            spec = fakes.get_search_spec(marker='non-existing')
            api.users_get(ctx, spec, session=self.sess)
        with testtools.ExpectedException(exc.BadInput):
            spec = fakes.get_search_spec(marker=fakes.FAKE_UUID1)
            api.users_get(ctx, spec, session=self.sess)

    def test_user_key_create_bad_data(self):
        ctx = mock.Mock()
        e_patcher = mock.patch('procession.db.api._exists')
        e_mock = e_patcher.start()

        self.addCleanup(e_patcher.stop)

        e_mock.return_value = True
        user_info = {}
        with testtools.ExpectedException(ValueError):
            api.user_key_create(ctx, 123, user_info)

    def test_user_key_create_user_not_found(self):
        ctx = mock.Mock()
        key_info = {'fingerprint': '1234',
                    'public_key': 'blah'}
        with testtools.ExpectedException(exc.NotFound):
            api.user_key_create(ctx, fakes.FAKE_UUID1, key_info)
