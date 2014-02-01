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

    def test_org_create_bad_data(self):
        ctx = mock.Mock()
        org_info = {}
        with testtools.ExpectedException(ValueError):
            api.organization_create(ctx, org_info)

    def test_org_delete_bad_input(self):
        ctx = mock.Mock()
        org_id = 'notauuid'
        with testtools.ExpectedException(exc.BadInput):
            api.organization_delete(ctx, org_id, session=self.sess)

    def test_org_delete_not_found(self):
        ctx = mock.Mock()
        with testtools.ExpectedException(exc.NotFound):
            api.organization_delete(ctx, fakes.FAKE_UUID1, session=self.sess)

    def test_org_create_invalid_attr(self):
        ctx = mock.Mock()
        org_info = {
            'display_name': 'foo org display',
            'org_name': 'foo org',
            'notanattr': True
        }
        with testtools.ExpectedException(TypeError):
            api.organization_create(ctx, org_info, session=self.sess)

    def test_org_create_parent_not_found(self):
        ctx = mock.Mock()
        org_info = {
            'display_name': 'foo org display',
            'org_name': 'foo org',
            'parent_organization_id': fakes.FAKE_UUID1
        }
        with testtools.ExpectedException(exc.NotFound):
            api.organization_create(ctx, org_info, session=self.sess)

    def test_org_create_parent_invalid(self):
        ctx = mock.Mock()
        org_info = {
            'display_name': 'foo org display',
            'org_name': 'foo org',
            'parent_organization_id': 'baduuid'
        }
        with testtools.ExpectedException(exc.BadInput):
            api.organization_create(ctx, org_info, session=self.sess)

    def test_org_crud(self):
        ctx = mock.Mock()
        org_info = {
            'display_name': 'root 1 display',
            'org_name': 'root 1 org'
        }
        ro1 = api.organization_create(ctx, org_info, session=self.sess)
        self.assertIsNotNone(ro1.id)
        ro1_id = ro1.id

        with testtools.ExpectedException(exc.Duplicate):
            api.organization_create(ctx, org_info, session=self.sess)

        self.assertEquals(ro1.display_name, org_info['display_name'])
        self.assertEquals(ro1.parent_organization_id, None)
        self.assertEquals(ro1.root_organization_id, ro1_id)

        # Add a child organization and verify that the root
        # organization is set correctly.
        org_info = {
            'display_name': 'root 1-a display',
            'org_name': 'root 1-a org',
            'parent_organization_id': ro1_id
        }
        ro1a = api.organization_create(ctx, org_info, session=self.sess)
        ro1a_id = ro1a.id

        self.assertEquals(ro1a.root_organization_id, ro1_id)

        # Validate that the slug is the combination of the parent slug
        # and the organization name
        self.assertEquals(ro1a.slug, ro1.slug + '-root-1-a-org')

        spec = fakes.get_search_spec()
        all_orgs = api.organizations_get(ctx, spec)
        self.assertThat(all_orgs, matchers.HasLength(2))

        # Ensure adding a child organization to the same parent with
        # the same organization name raises a Duplicate but that we can
        # still create an organization in a different root organization
        # with the same org name.
        org_info = {
            'display_name': 'root 1-a display',
            'org_name': 'root 1-a org',
            'parent_organization_id': ro1_id
        }
        with testtools.ExpectedException(exc.Duplicate):
            api.organization_create(ctx, org_info, session=self.sess)

        # Add a child organization and verify that the root
        # organization is set correctly.
        org_info = {
            'display_name': 'root 2 display',
            'org_name': 'root 2 org'
        }
        ro2 = api.organization_create(ctx, org_info, session=self.sess)
        ro2_id = ro2.id
        self.addCleanup(api.organization_delete, ctx, ro2_id,
                        session=self.sess)
        org_info = {
            'display_name': 'root 1-a display',
            'org_name': 'root 1-a org',  # Same name as ro1a, but diff root
            'parent_organization_id': ro2_id
        }
        ro2a = api.organization_create(ctx, org_info, session=self.sess)
        self.assertEquals(ro2a.parent_organization_id, ro2_id)

        api.organization_delete(ctx, ro1_id, session=self.sess)

        with testtools.ExpectedException(exc.NotFound):
            api.organization_delete(ctx, ro1_id, session=self.sess)

        # Verify child regions are all deleted
        with testtools.ExpectedException(exc.NotFound):
            api.organization_get_by_pk(ctx, ro1a_id, session=self.sess)

    def test_org_sharding(self):
        # We construct a set of org trees and perform update and delete
        # operations on them, verifying that the sharded nested sets model
        # is working properly and one tree does not affect another.
        #
        # We create a set of trees like so:
        #
        # root 1 tree:
        #
        # A1
        # |
        # -- B1
        # |  |
        # |  --C1
        # |    |
        # |    -- D1
        # |    |
        # |    -- E1
        # |
        # -- F1
        #    |
        #    -- G1
        #       |
        #       -- H1
        #
        # root 2 tree:
        #
        # A2
        # |
        # -- B2
        # |  |
        # |  --C2
        ctx = mock.Mock()
        orgs = {
            'A1': {},
            'B1': {'parent': 'A1'},
            'C1': {'parent': 'B1'},
            'D1': {'parent': 'C1'},
            'E1': {'parent': 'C1'},
            'F1': {'parent': 'A1'},
            'G1': {'parent': 'F1'},
            'H1': {'parent': 'G1'},
            'A2': {},
            'B2': {'parent': 'A2'},
            'C2': {'parent': 'B2'}
        }

        for o_name, org_dict in sorted(orgs.items()):
            org_info = {
                'org_name': o_name,
                'display_name': o_name
            }
            if 'parent' in org_dict:
                parent = org_dict['parent']
                org_info['parent_organization_id'] = orgs[parent]['obj'].id

            o = api.organization_create(ctx, org_info, session=self.sess)
            orgs[o_name]['obj'] = o

        spec = fakes.get_search_spec(limit=20)
        all_orgs = api.organizations_get(ctx, spec)
        expected_length = len(orgs)
        self.assertThat(all_orgs, matchers.HasLength(expected_length))

        b1_id = orgs['B1']['obj'].id
        subtree = api.organization_get_subtree(ctx, b1_id, session=self.sess)
        expected_length = 4  # B1 -> C1 -> (D1, E1)
        self.assertThat(subtree, matchers.HasLength(expected_length))

        f1_id = orgs['F1']['obj'].id
        api.organization_delete(ctx, f1_id)

        all_orgs = api.organizations_get(ctx, spec)
        expected_length = len(orgs) - 3  # F1 -> G1 -> H1 should be gone
        self.assertThat(all_orgs, matchers.HasLength(expected_length))

        a1_id = orgs['A1']['obj'].id
        api.organization_delete(ctx, a1_id)

        all_orgs = api.organizations_get(ctx, spec)
        expected_length = 3  # Only A2 -> B2 -> C2 should be left
        self.assertThat(all_orgs, matchers.HasLength(expected_length))

        a2_id = orgs['A2']['obj'].id
        api.organization_delete(ctx, a2_id)

        all_orgs = api.organizations_get(ctx, spec)
        self.assertThat(all_orgs, matchers.HasLength(0))

    def test_org_get_by_pk_not_found(self):
        ctx = mock.Mock()
        with testtools.ExpectedException(exc.NotFound):
            api.organization_get_by_pk(ctx, fakes.FAKE_UUID1,
                                       session=self.sess)

    def test_org_group_create_bad_data(self):
        ctx = mock.Mock()
        group_info = {}
        with testtools.ExpectedException(ValueError):
            api.organization_group_create(ctx, group_info)

    def test_org_group_delete_bad_input(self):
        ctx = mock.Mock()
        group_id = 'notauuid'
        with testtools.ExpectedException(exc.BadInput):
            api.organization_group_delete(ctx, group_id, session=self.sess)

    def test_org_group_delete_not_found(self):
        ctx = mock.Mock()
        with testtools.ExpectedException(exc.NotFound):
            api.organization_group_delete(ctx, fakes.FAKE_UUID1,
                                          session=self.sess)

    def test_org_group_create_invalid_attr(self):
        ctx = mock.Mock()
        group_info = {
            'display_name': 'foo group display',
            'group_name': 'foo group',
            'root_organization_id': fakes.FAKE_UUID1,
            'notanattr': True
        }
        with testtools.ExpectedException(TypeError):
            api.organization_group_create(ctx, group_info, session=self.sess)

    def test_org_group_create_root_not_root(self):
        ctx = mock.Mock()
        org_info = {
            'display_name': 'root 1 display',
            'org_name': 'root 1 org'
        }
        ro1 = api.organization_create(ctx, org_info, session=self.sess)
        ro1_id = ro1.id
        self.addCleanup(api.organization_delete, ctx, ro1_id, session=self.sess)

        org_info = {
            'display_name': 'root 1-a display',
            'org_name': 'root 1-a org',
            'parent_organization_id': ro1_id
        }
        ro1a = api.organization_create(ctx, org_info, session=self.sess)
        ro1a_id = ro1a.id

        group_info = {
            'display_name': 'foo group display',
            'group_name': 'foo org',
            'root_organization_id': ro1a_id
        }
        with testtools.ExpectedException(exc.BadInput):
            api.organization_group_create(ctx, group_info, session=self.sess)

    def test_org_group_create_root_not_found(self):
        ctx = mock.Mock()
        group_info = {
            'display_name': 'foo org display',
            'group_name': 'foo org',
            'root_organization_id': fakes.FAKE_UUID1
        }
        with testtools.ExpectedException(exc.NotFound):
            api.organization_group_create(ctx, group_info, session=self.sess)

    def test_org_group_create_invalid_root(self):
        ctx = mock.Mock()
        group_info = {
            'display_name': 'foo org display',
            'group_name': 'foo org',
            'root_organization_id': 'notauuid'
        }
        with testtools.ExpectedException(exc.BadInput):
            api.organization_group_create(ctx, group_info, session=self.sess)

    def test_org_group_crud(self):
        ctx = mock.Mock()
        org_info = {
            'display_name': 'root 1 display',
            'org_name': 'root 1 org'
        }
        ro1 = api.organization_create(ctx, org_info, session=self.sess)
        ro1_id = ro1.id

        group_info = {
            'display_name': 'root 1 group display',
            'group_name': 'root 1 group',
            'root_organization_id': ro1_id
        }
        rg1 = api.organization_group_create(ctx, group_info, session=self.sess)
        self.assertIsNotNone(rg1.id)
        rg1_id = rg1.id

        with testtools.ExpectedException(exc.Duplicate):
            api.organization_group_create(ctx, group_info, session=self.sess)

        self.assertEquals(rg1.display_name, group_info['display_name'])
        self.assertEquals(rg1.root_organization_id, ro1_id)
        self.assertEquals('root-1-org-root-1-group', rg1.slug)

        group_info = {
            'display_name': 'root 1 group 2 display',
            'group_name': 'root 1 group 2',
            'root_organization_id': ro1_id
        }
        rg2 = api.organization_group_create(ctx, group_info, session=self.sess)
        rg2_id = rg2.id

        spec = fakes.get_search_spec(limit=20)
        all_groups = api.organization_groups_get(ctx, spec)
        expected_length = 2
        self.assertThat(all_groups, matchers.HasLength(expected_length))

        api.organization_group_delete(ctx, rg2_id, session=self.sess)

        with testtools.ExpectedException(exc.NotFound):
            api.organization_group_delete(ctx, rg2_id, session=self.sess)

        # Delete the root organization and make sure the group is also deleted
        api.organization_delete(ctx, ro1_id, session=self.sess)

        with testtools.ExpectedException(exc.NotFound):
            api.organization_group_delete(ctx, rg2_id, session=self.sess)

    def test_org_group_get_by_pk_not_found(self):
        ctx = mock.Mock()
        with testtools.ExpectedException(exc.NotFound):
            api.organization_group_get_by_pk(ctx, fakes.FAKE_UUID1,
                                             session=self.sess)

    def test_user_create_bad_data(self):
        ctx = mock.Mock()
        user_info = {}
        with testtools.ExpectedException(ValueError):
            api.user_create(ctx, user_info)

    def test_user_update_bad_data(self):
        ctx = mock.Mock()
        user_info = {
            'display_name': 'foo bar display',
            'user_name': 'foo bar',
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
        user_id = 'notauuid'
        with testtools.ExpectedException(exc.BadInput):
            api.user_delete(ctx, user_id, session=self.sess)

    def test_user_update_bad_input(self):
        ctx = mock.Mock()
        user_id = 'notauuid'
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
            'display_name': 'foo bar display',
            'user_name': 'foo bar',
            'email': 'foo@example.com',
            'notanattr': True
        }
        with testtools.ExpectedException(TypeError):
            api.user_create(ctx, user_info, session=self.sess)

    def test_user_crud(self):
        ctx = mock.Mock()
        user_info = {
            'display_name': 'foo bar display',
            'user_name': 'foo bar',
            'email': 'foo@example.com'
        }
        u = api.user_create(ctx, user_info, session=self.sess)
        self.assertIsNotNone(u.id)

        with testtools.ExpectedException(exc.Duplicate):
            u = api.user_create(ctx, user_info, session=self.sess)

        self.assertEquals(u.display_name, user_info['display_name'])

        # Validate slug creation correct
        self.assertEquals(u.slug, 'foo-bar')

        # Test get by PK and get by slug both return the user
        u2 = api.user_get_by_pk(ctx, u.id, session=self.sess)
        self.assertEquals(u, u2)
        u3 = api.user_get_by_pk(ctx, u.slug, session=self.sess)
        self.assertEquals(u, u3)

        # Test get by bad slug still returns a NotFound...
        with testtools.ExpectedException(exc.NotFound):
            api.user_get_by_pk(ctx, 'noexisting', session=self.sess)

        update_info = {
            'display_name': 'bar',
            'user_name': 'fooey'
        }
        u = api.user_update(ctx, u.id, update_info, session=self.sess,
                            commit=False)
        self.assertEquals('bar', u.display_name)
        # Verify that the slug has changed appropriately
        self.assertEquals('fooey', u.slug)
        # Verify that the session was not committed since we did not
        # specify a commit kwarg
        self.assertTrue(self.sess.dirty)
        # Now do the same thing and verify the session was committed
        u = api.user_update(ctx, u.id, update_info, session=self.sess)
        self.assertFalse(self.sess.dirty)

        # Test an invalid attribute set
        update_info = {
            'notanattr': True
        }
        with testtools.ExpectedException(exc.BadInput):
            api.user_update(ctx, u.id, update_info, session=self.sess)

        # Try to make a user name that will produce the same slug as
        # an existing user record and verify that a Duplicate is raised
        user_info = {
            'display_name': 'baz display',
            'user_name': 'baz',
            'email': 'baz@example.com'
        }
        u2 = api.user_create(ctx, user_info, session=self.sess)
        self.addCleanup(api.user_delete, ctx, u2.id, session=self.sess)
        update_info = {
            'user_name': 'fooey'
        }
        with testtools.ExpectedException(exc.Duplicate):
            api.user_update(ctx, u2.id, update_info, session=self.sess,
                            commit=True)

        # Now we test valid addition of public SSH keys to the
        # new user object.
        key_info = {'fingerprint': fakes.FAKE_FINGERPRINT1,
                    'public_key': 'blah'}
        k = api.user_key_create(ctx, u.id, key_info, session=self.sess,
                                commit=True)
        self.assertEquals(k.fingerprint, key_info['fingerprint'])

        spec = fakes.get_search_spec(filters=dict(user_id=u.id))
        keys = api.user_keys_get(ctx, spec)
        self.assertThat(keys, matchers.HasLength(1))
        self.assertThat(keys, matchers.Contains(k))

        # Try to add a new key with same fingerprint
        with testtools.ExpectedException(exc.Duplicate):
            api.user_key_create(ctx, u.id, key_info, session=self.sess)

        # Add another key and then delete the key manually
        key_info = {'fingerprint': fakes.FAKE_FINGERPRINT2,
                    'public_key': 'blah'}
        k = api.user_key_create(ctx, u.id, key_info, commit=True)
        self.assertEquals(k.fingerprint, key_info['fingerprint'])

        spec = fakes.get_search_spec(filters=dict(user_id=u.id))
        keys = api.user_keys_get(ctx, spec)
        self.assertThat(keys, matchers.HasLength(2))
        self.assertThat(keys, matchers.Contains(k))

        k2 = api.user_key_get_by_pk(ctx, u.id, k.fingerprint,
                                    session=self.sess)
        self.assertEqual(k, k2)

        api.user_key_delete(ctx, u.id, k.fingerprint, session=self.sess)
        keys = api.user_keys_get(ctx, spec)
        self.assertThat(keys, matchers.HasLength(1))
        self.assertThat(keys, matchers.Not(matchers.Contains(k)))

        api.user_delete(ctx, u.id, session=self.sess)

        with testtools.ExpectedException(exc.NotFound):
            api.user_delete(ctx, u.id, session=self.sess)

        # Make sure our relations are also deleted
        keys = api.user_keys_get(ctx, spec, session=self.sess)
        self.assertThat(keys, matchers.HasLength(0))

    def test_user_get_by_pk_not_found(self):
        ctx = mock.Mock()
        with testtools.ExpectedException(exc.NotFound):
            api.user_get_by_pk(ctx, fakes.FAKE_UUID1, session=self.sess)

    def test_users_get(self):
        ctx = mock.Mock()
        user_infos = [
            {
                'display_name': 'foo display',
                'user_name': 'foo',
                'email': 'foo@example.com'
            },
            {
                'display_name': 'bar',
                'user_name': 'bar',
                'email': 'bar@example.com'
            },
            {
                'display_name': 'baz',
                'user_name': 'baz',
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

    def test_user_key_get_by_pk_not_found(self):
        ctx = mock.Mock()
        with testtools.ExpectedException(exc.NotFound):
            api.user_key_get_by_pk(ctx, fakes.FAKE_UUID1,
                                   fakes.FAKE_FINGERPRINT1, session=self.sess)

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

    def test_user_key_delete_exceptions(self):
        ctx = mock.Mock()
        user_info = {
            'display_name': 'foo',
            'user_name': 'foo',
            'email': 'foo@example.com'
        }
        u = api.user_create(ctx, user_info, session=self.sess)
        self.assertIsNotNone(u.id)
        self.addCleanup(api.user_delete, ctx, u.id, session=self.sess)

        with testtools.ExpectedException(exc.NotFound):
            api.user_key_delete(ctx, u.id, fakes.FAKE_FINGERPRINT1,
                                session=self.sess)

        with testtools.ExpectedException(exc.BadInput):
            api.user_key_delete(ctx, u.id, '1234', session=self.sess)
