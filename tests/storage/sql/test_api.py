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

# NOTE: These particular unit tests are more than just unit tests. It is partly
# a functional test of the DB API layer as well, since mocking out all of
# SQLAlchemy was not particularly nice, nor all that useful in identifying
# bugs. So, these tests do actually execute the various database queries
# against an SQLite database backend and verify things like transaction safety.

import mock
import testtools
from testtools import matchers

from procession import exc
from procession import objects
from procession import store
from procession.storage.sql import api

from tests import base
from tests import fakes


class TestDbApi(base.UnitTest):

    def setUp(self):
        super(TestDbApi, self).setUp()
        self.sess = session.get_session()

    def _new_org(self, values):
        """
        Return a new org based on a supplied dict of field values.
        """
        return objects.Organization.from_dict(values)

    def _new_group(self, values):
        """
        Return a new org based on a supplied dict of field values.
        """
        return objects.Group.from_dict(values)


class TestOrganizations(TestDbApi):

    def test_org_delete_not_found(self):
        ctx = mock.Mock()
        with testtools.ExpectedException(exc.NotFound):
            api.organization_delete(ctx, fakes.NO_EXIST_UUID, session=self.sess)

    def test_org_create_parent_not_found(self):
        ctx = mock.Mock()
        org_info = {
            'name': 'foo org',
            'parentOrganizationId': fakes.NO_EXIST_UUID
        }
        org = self._new_org(org_info)
        with testtools.ExpectedException(exc.NotFound):
            api.organization_create(ctx, org, session=self.sess)

    def test_org_crud(self):
        ctx = mock.Mock()
        org_info = {
            'name': 'root 1 org'
        }
        org1 = self._new_org(org_info)
        ro1 = api.organization_create(ctx, org1, session=self.sess)
        self.assertIsNotNone(ro1.id)
        ro1_id = ro1.id

        with testtools.ExpectedException(exc.Duplicate):
            api.organization_create(ctx, org1, session=self.sess)

        self.assertEquals(ro1.name, org_info['name'])
        self.assertEquals(ro1.parentOrganizationId, None)
        self.assertEquals(ro1.rootOrganizationId, ro1_id)

        # Add a child organization and verify that the root
        # organization is set correctly.
        org_info = {
            'name': 'root 1-a org',
            'parentOrganizationId': ro1_id
        }
        org1a = self._new_org(org_info)
        ro1a = api.organization_create(ctx, org1a, session=self.sess)
        ro1a_id = ro1a.id

        self.assertEquals(ro1a.rootOrganizationId, ro1_id)

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
        with testtools.ExpectedException(exc.Duplicate):
            api.organization_create(ctx, org1a, session=self.sess)

        # Add a child organization and verify that the root
        # organization is set correctly.
        org_info = {
            'name': 'root 2 org'
        }
        org2 = self._new_org(org_info)
        ro2 = api.organization_create(ctx, org2, session=self.sess)
        ro2_id = ro2.id
        self.addCleanup(api.organization_delete, ctx, ro2_id,
                        session=self.sess)
        org_info = {
            'name': 'root 1-a org',  # Same name as ro1a, but diff root
            'parentOrganizationId': ro2_id
        }
        org2a = self._new_org(org_info)
        ro2a = api.organization_create(ctx, org2a, session=self.sess)
        self.assertEquals(ro2a.parentOrganizationId, ro2_id)

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
                'name': o_name,
            }
            if 'parent' in org_dict:
                parent = org_dict['parent']
                org_info['parentOrganizationId'] = orgs[parent]['obj'].id

            org = self._new_org(org_info)
            o = api.organization_create(ctx, org, session=self.sess)
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
            api.organization_get_by_pk(ctx, fakes.NO_EXIST_UUID,
                                       session=self.sess)

    def test_group_delete_not_found(self):
        ctx = mock.Mock()
        with testtools.ExpectedException(exc.NotFound):
            api.group_delete(ctx, fakes.NO_EXIST_UUID, session=self.sess)

    def test_group_create_root_not_root(self):
        ctx = mock.Mock()
        org_info = {
            'name': 'root 1 org'
        }
        org1 = self._new_org(org_info)
        ro1 = api.organization_create(ctx, org1, session=self.sess)
        ro1_id = ro1.id
        self.addCleanup(api.organization_delete, ctx, ro1_id,
                        session=self.sess)

        org_info = {
            'name': 'root 1-a org',
            'parentOrganizationId': ro1_id
        }
        org1a = self._new_org(org_info)
        ro1a = api.organization_create(ctx, org1a, session=self.sess)
        ro1a_id = ro1a.id

        group_info = {
            'name': 'foo org',
            'rootOrganizationId': ro1a_id
        }
        group = self._new_group(group_info)
        with testtools.ExpectedException(exc.BadInput):
            api.group_create(ctx, group, session=self.sess)

    def test_group_create_root_not_found(self):
        ctx = mock.Mock()
        group_info = {
            'name': 'foo org',
            'rootOrganizationId': fakes.NO_EXIST_UUID
        }
        group = self._new_group(group_info)
        with testtools.ExpectedException(exc.NotFound):
            api.group_create(ctx, group, session=self.sess)

    def test_group_update_not_found(self):
        ctx = mock.Mock()
        group_info = {
            'name': 'foo org',
            'rootOrganizationId': 'notauuid'
        }
        with testtools.ExpectedException(exc.NotFound):
            api.group_update(ctx, fakes.NO_EXIST_UUID, group_info,
                             session=self.sess)

    def test_group_update_bad_input(self):
        ctx = mock.Mock()

        org_info = {
            'name': 'root 1 org'
        }
        org1 = self._new_org(org_info)
        ro1 = api.organization_create(ctx, org1, session=self.sess)
        ro1_id = ro1.id
        self.addCleanup(api.organization_delete, ctx, ro1_id,
                        session=self.sess)

        group_info = {
            'name': 'group 1',
            'rootOrganizationId': ro1_id
        }
        group = self._new_group(group_info)
        g1 = api.group_create(ctx, group, session=self.sess)
        g1_id = g1.id

        group_info = {
            'name': 'group 2',
            'rootOrganizationId': ro1_id
        }
        group = self._new_group(group_info)
        g2 = api.group_create(ctx, group, session=self.sess)
        g2_id = g2.id

        # Test that trying to update the group with a null root
        # organization raises an error
        update_info = {
            'name': 'group 1',
            'rootOrganizationId': None  # Required...
        }
        with testtools.ExpectedException(exc.BadInput):
            api.group_update(ctx, g1_id, update_info, session=self.sess)

        # Test that trying to update the group's name to a name of another
        # group within the same root organization raises an error
        update_info = {
            'name': 'group 1'
        }
        with testtools.ExpectedException(exc.Duplicate):
            api.group_update(ctx, g2_id, update_info, session=self.sess)

    def test_group_crud(self):
        ctx = mock.Mock()
        org_info = {
            'name': 'root 1 org'
        }
        org1 = self._new_org(org_info)
        ro1 = api.organization_create(ctx, org1, session=self.sess)
        ro1_id = ro1.id

        org_info = {
            'name': 'root 1-a org',
            'parentOrganizationId': ro1_id
        }
        org1a = self._new_org(org_info)
        ro1a = api.organization_create(ctx, org1a, session=self.sess)
        ro1a_id = ro1a.id

        group_info = {
            'name': 'root 1 group',
            'rootOrganizationId': ro1_id
        }
        group = self._new_group(group_info)
        rg1 = api.group_create(ctx, group, session=self.sess)
        self.assertIsNotNone(rg1.id)

        with testtools.ExpectedException(exc.Duplicate):
            api.group_create(ctx, group, session=self.sess)

        self.assertEquals(rg1.name, group_info['name'])
        self.assertEquals(rg1.rootOrganizationId, ro1_id)
        self.assertEquals('root-1-org-root-1-group', rg1.slug)

        group_info = {
            'name': 'root 1 group 2',
            'rootOrganizationId': ro1_id
        }
        group = self._new_group(group_info)
        rg2 = api.group_create(ctx, group, session=self.sess)
        rg2_id = rg2.id

        spec = fakes.get_search_spec(limit=20)
        all_groups = api.groups_get(ctx, spec)
        expected_length = 2
        self.assertThat(all_groups, matchers.HasLength(expected_length))

        update_info = {
            'name': 'group 2',
            'rootOrganizationId': ro1_id
        }
        tmp_g2 = api.group_update(ctx, rg2_id, update_info, session=self.sess)

        self.assertEquals('root-1-org-group-2', tmp_g2.slug)

        # Test that trying to update the group to a non-root
        # organization also raises an error
        update_info = {
            'name': 'group 2',
            'rootOrganizationId': ro1a_id
        }
        with testtools.ExpectedException(exc.BadInput):
            api.group_update(ctx, rg2_id, update_info, session=self.sess)

        api.group_delete(ctx, rg2_id, session=self.sess)

        with testtools.ExpectedException(exc.NotFound):
            api.group_delete(ctx, rg2_id, session=self.sess)

        # Delete the root organization and make sure the group is also deleted
        api.organization_delete(ctx, ro1_id, session=self.sess)

        with testtools.ExpectedException(exc.NotFound):
            api.group_delete(ctx, rg2_id, session=self.sess)

    def test_group_get_by_pk_not_found(self):
        ctx = mock.Mock()
        with testtools.ExpectedException(exc.NotFound):
            api.group_get_by_pk(ctx, fakes.NO_EXIST_UUID, session=self.sess)

    def test_user_delete_not_found(self):
        ctx = mock.Mock()
        with testtools.ExpectedException(exc.NotFound):
            api.user_delete(ctx, fakes.NO_EXIST_UUID, session=self.sess)

    def test_user_update_not_found(self):
        ctx = mock.Mock()
        with testtools.ExpectedException(exc.NotFound):
            api.user_update(ctx, fakes.NO_EXIST_UUID, {}, session=self.sess)

    def test_user_crud(self):
        ctx = mock.Mock()
        user_info = {
            'name': 'foo bar',
            'email': 'foo@example.com'
        }
        u = api.user_create(ctx, user_info, session=self.sess)
        self.assertIsNotNone(u.id)

        with testtools.ExpectedException(exc.Duplicate):
            u = api.user_create(ctx, user_info, session=self.sess)

        self.assertEquals(u.name, user_info['name'])

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
            'name': 'fooey'
        }
        u = api.user_update(ctx, u.id, update_info, session=self.sess,
                            commit=False)
        # Verify that the slug has changed appropriately
        self.assertEquals('fooey', u.slug)
        # Verify that the session was not committed since we did not
        # specify a commit kwarg
        self.assertTrue(self.sess.dirty)
        # Now do the same thing and verify the session was committed
        u = api.user_update(ctx, u.id, update_info, session=self.sess)
        self.assertFalse(self.sess.dirty)

        # Try to make a user name that will produce the same slug as
        # an existing user record and verify that a Duplicate is raised
        user_info = {
            'name': 'baz',
            'email': 'baz@example.com'
        }
        u2 = api.user_create(ctx, user_info, session=self.sess)
        self.addCleanup(api.user_delete, ctx, u2.id, session=self.sess)
        update_info = {
            'name': 'fooey'
        }
        with testtools.ExpectedException(exc.Duplicate):
            api.user_update(ctx, u2.id, update_info, session=self.sess,
                            commit=True)

        # Now we test valid addition of public SSH keys to the
        # new user object.
        key_info = {'fingerprint': fakes.FAKE_FINGERPRINT1,
                    'publicKey': 'blah'}
        k = api.user_key_create(ctx, u.id, key_info, session=self.sess,
                                commit=True)
        self.assertEquals(k.fingerprint, key_info['fingerprint'])

        spec = fakes.get_search_spec(filters=dict(userId=u.id))
        keys = api.user_keys_get(ctx, spec)
        self.assertThat(keys, matchers.HasLength(1))
        self.assertThat(keys, matchers.Contains(k))

        # Try to add a new key with same fingerprint
        with testtools.ExpectedException(exc.Duplicate):
            api.user_key_create(ctx, u.id, key_info, session=self.sess)

        # Add another key and then delete the key manually
        key_info = {'fingerprint': fakes.FAKE_FINGERPRINT2,
                    'publicKey': 'blah'}
        k = api.user_key_create(ctx, u.id, key_info, commit=True)
        self.assertEquals(k.fingerprint, key_info['fingerprint'])

        spec = fakes.get_search_spec(filters=dict(userId=u.id))
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

    def test_user_group_membership(self):
        ctx = mock.Mock()
        org_info = {
            'name': 'org'
        }
        org = self._new_org(org_info)
        o = api.organization_create(ctx, org, session=self.sess)
        o_id = o.id

        # Not adding a cleanup, because part of this test is to ensure
        # that deleting the organization deletes the groups associated
        # with that organization, and deletes the user/group membership
        # records associated with that group.

        group_info = {
            'name': 'group',
            'rootOrganizationId': o_id
        }
        group = self._new_group(group_info)
        g = api.group_create(ctx, group, session=self.sess)
        g_id = g.id

        group_info = {
            'name': 'group 2',
            'rootOrganizationId': o_id
        }
        group = self._new_group(group_info)
        g2 = api.group_create(ctx, group, session=self.sess)
        g2_id = g2.id

        user_info = {
            'name': 'foo',
            'email': 'foo@example.com'
        }
        u = api.user_create(ctx, user_info, session=self.sess)
        u_id = u.id
        self.addCleanup(api.user_delete, ctx, u_id, session=self.sess)

        groups = api.user_groups_get(ctx, u_id, session=self.sess)
        self.assertThat(groups, matchers.HasLength(0))

        users = api.group_users_get(ctx, g_id, session=self.sess)
        self.assertThat(users, matchers.HasLength(0))

        # We should not be able to add a non-existing user to a
        # real group, nor a real user to a non-existing group.
        with testtools.ExpectedException(exc.NotFound):
            api.user_group_add(ctx, u_id, fakes.NO_EXIST_UUID, session=self.sess)
        with testtools.ExpectedException(exc.NotFound):
            api.user_group_add(ctx, fakes.NO_EXIST_UUID, g_id, session=self.sess)

        ug = api.user_group_add(ctx, u_id, g_id, session=self.sess)
        self.assertEquals(u_id, ug.userId)
        self.assertEquals(g_id, ug.groupId)

        groups = api.user_groups_get(ctx, u_id, session=self.sess)
        self.assertThat(groups, matchers.HasLength(1))

        users = api.group_users_get(ctx, g_id, session=self.sess)
        self.assertThat(users, matchers.HasLength(1))

        # Ensure that adding the same user group membership does not
        # do anything other than return the same u/g membership record
        # as above -- i.e. it does not raise Duplicate.
        tmp_ug = api.user_group_add(ctx, u_id, g_id, session=self.sess)
        self.assertEquals(ug, tmp_ug)

        # Add and remove a second group membership for the user
        ug = api.user_group_add(ctx, u_id, g2_id, session=self.sess)
        self.assertEquals(u_id, ug.userId)
        self.assertEquals(g2_id, ug.groupId)

        groups = api.user_groups_get(ctx, u_id, session=self.sess)
        self.assertThat(groups, matchers.HasLength(2))

        users = api.group_users_get(ctx, g2_id, session=self.sess)
        self.assertThat(users, matchers.HasLength(1))

        api.user_group_remove(ctx, u_id, g2_id, session=self.sess)

        groups = api.user_groups_get(ctx, u_id, session=self.sess)
        self.assertThat(groups, matchers.HasLength(1))

        users = api.group_users_get(ctx, g2_id, session=self.sess)
        self.assertThat(users, matchers.HasLength(0))

        # We should not be able to remove a group from a non-existing user
        with testtools.ExpectedException(exc.NotFound):
            api.user_group_remove(ctx, fakes.NO_EXIST_UUID, g_id,
                                  session=self.sess)

        # However, trying to remove a non-existing group from a real user
        # should simply return None.
        api.user_group_remove(ctx, u_id, fakes.FAKE_UUID1, session=self.sess)

        # Deleting the organization should delete the group and any
        # associated user group membership records.
        api.organization_delete(ctx, o_id, session=self.sess)

        groups = api.user_groups_get(ctx, u_id, session=self.sess)
        self.assertThat(groups, matchers.HasLength(0))

    def test_user_get_by_pk_not_found(self):
        ctx = mock.Mock()
        with testtools.ExpectedException(exc.NotFound):
            api.user_get_by_pk(ctx, fakes.FAKE_UUID1, session=self.sess)

    def test_users_get(self):
        ctx = mock.Mock()
        user_infos = [
            {
                'name': 'foo',
                'email': 'foo@example.com'
            },
            {
                'name': 'bar',
                'email': 'bar@example.com'
            },
            {
                'name': 'baz',
                'email': 'baz@example.com'
            },
        ]
        # The IDs of the users, indexed by email...
        userIds = {}
        for user_info in user_infos:
            u = api.user_create(ctx, user_info, session=self.sess)
            self.assertIsNotNone(u.id)
            self.addCleanup(api.user_delete, ctx, u.id, session=self.sess)
            userIds[user_info['email']] = u.id

        # Empty fake search spec has a limit of 2, so test
        # that with an empty spec, we get 2 records, and that
        # they are the last two records created since the
        # default sort order on the User model is created_at desc.
        spec = fakes.get_search_spec()
        users = api.users_get(ctx, spec, session=self.sess)
        self.assertThat(users, matchers.HasLength(2))
        user_names = [u.name for u in users]
        self.assertThat(user_names, matchers.Not(matchers.Contains('foo')))

        # Now test the same thing, only override the ordering to order
        # over the email address.
        spec = fakes.get_search_spec(order_by=["email desc"])
        users = api.users_get(ctx, spec, session=self.sess)
        self.assertThat(users, matchers.HasLength(2))
        user_names = [u.name for u in users]
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
                                     marker=userIds['baz@example.com'])
        users = api.users_get(ctx, spec, session=self.sess)
        self.assertThat(users, matchers.HasLength(1))
        self.assertEquals(users[0].email, 'bar@example.com')

        # Test pagination results for sorting by asc createdOn, with
        # a marker of the bar user. This tests the scenario in pagination
        # where we must add an additional sort on a unique column when
        # the user has not supplied a unique sort order.
        spec = fakes.get_search_spec(order_by=["createdOn asc"],
                                     marker=userIds['bar@example.com'])
        users = api.users_get(ctx, spec, session=self.sess)
        self.assertThat(users, matchers.HasLength(1))
        self.assertEquals(users[0].email, 'baz@example.com')

        # Verify that supplying a marker that doesn't exist in the
        # database raises a BadInput.
        with testtools.ExpectedException(exc.BadInput):
            spec = fakes.get_search_spec(marker='non-existing')
            api.users_get(ctx, spec, session=self.sess)

    def test_user_key_get_by_pk_not_found(self):
        ctx = mock.Mock()
        with testtools.ExpectedException(exc.NotFound):
            api.user_key_get_by_pk(ctx, fakes.NO_EXIST_UUID,
                                   fakes.FAKE_FINGERPRINT1, session=self.sess)

    def test_user_key_create_user_not_found(self):
        ctx = mock.Mock()
        key_info = {'fingerprint': '1234',
                    'publicKey': 'blah'}
        with testtools.ExpectedException(exc.NotFound):
            api.user_key_create(ctx, fakes.FAKE_UUID1, key_info)

    def test_user_key_delete_exceptions(self):
        ctx = mock.Mock()
        user_info = {
            'name': 'foo',
            'email': 'foo@example.com'
        }
        u = api.user_create(ctx, user_info, session=self.sess)
        self.assertIsNotNone(u.id)
        self.addCleanup(api.user_delete, ctx, u.id, session=self.sess)

        with testtools.ExpectedException(exc.NotFound):
            api.user_key_delete(ctx, u.id, fakes.FAKE_FINGERPRINT1,
                                session=self.sess)

    def test_domain_get_by_pk_not_found(self):
        ctx = mock.Mock()
        with testtools.ExpectedException(exc.NotFound):
            api.domain_get_by_pk(ctx, fakes.FAKE_UUID1, session=self.sess)

    def test_domain_create_owner_not_found(self):
        ctx = mock.Mock()
        info = {'name': 'my domain',
                'ownerId': fakes.NO_EXIST_UUID}
        with testtools.ExpectedException(exc.NotFound):
            api.domain_create(ctx, info)

    def test_domain_create_bad_data(self):
        ctx = mock.Mock()
        e_mock = self.patch('procession.db.api._exists')
        e_mock.return_value = True
        info = {}
        with testtools.ExpectedException(ValueError):
            api.domain_create(ctx, info)

        # Missing owner ID
        info = {
            'name': 'my domain'
        }
        with testtools.ExpectedException(ValueError):
            api.domain_create(ctx, info)

    def test_domain_create_invalid_attr(self):
        ctx = mock.Mock()
        info = {
            'name': 'foo group',
            'ownerId': fakes.FAKE_UUID1,
            'notanattr': True
        }
        with testtools.ExpectedException(TypeError):
            api.domain_create(ctx, info, session=self.sess)

    def test_domain_delete_exceptions(self):
        ctx = mock.Mock()
        with testtools.ExpectedException(exc.NotFound):
            api.domain_delete(ctx, fakes.NO_EXIST_UUID, session=self.sess)

    def test_domain_crud(self):
        ctx = mock.Mock()
        info = {
            'name': 'user 1',
            'email': 'user1@example.com'
        }
        u = api.user_create(ctx, info, session=self.sess)
        u_id = u.id
        self.addCleanup(api.user_delete, ctx, u_id, session=self.sess)

        info = {
            'name': 'user 2',
            'email': 'user2@example.com'
        }
        u2 = api.user_create(ctx, info, session=self.sess)
        u2_id = u2.id
        self.addCleanup(api.user_delete, ctx, u2_id, session=self.sess)

        info = {
            'name': 'my domain',
            'ownerId': u_id
        }
        d = api.domain_create(ctx, info, session=self.sess)
        d_id = d.id

        with testtools.ExpectedException(exc.Duplicate):
            api.domain_create(ctx, info, session=self.sess)

        self.assertEquals(d.name, info['name'])

        # Validate slug creation correct
        self.assertEquals(d.slug, 'my-domain')

        # Test get by PK and get by slug both return the user
        d2 = api.domain_get_by_pk(ctx, d_id, session=self.sess)
        self.assertEquals(d, d2)
        d3 = api.domain_get_by_pk(ctx, d.slug, session=self.sess)
        self.assertEquals(d, d3)

        # Test get by bad slug still returns a NotFound...
        with testtools.ExpectedException(exc.NotFound):
            api.domain_get_by_pk(ctx, 'noexisting', session=self.sess)

        info = {
            'name': 'my domain 2',
            'ownerId': u2_id
        }
        d2 = api.domain_create(ctx, info, session=self.sess)
        d2_id = d2.id
        self.addCleanup(api.domain_delete, ctx, d2_id, session=self.sess)

        info = {
            'name': 'foo domain 2'
        }
        tmp_d = api.domain_update(ctx, d2_id, info, session=self.sess)
        self.assertEquals(info['name'], tmp_d.name)
        self.assertEquals(u2_id, tmp_d.ownerId)

        # Can't update ownerId to a non-existing user
        with testtools.ExpectedException(exc.NotFound):
            info = {
                'ownerId': fakes.NO_EXIST_UUID
            }
            api.domain_update(ctx, d2_id, info, session=self.sess)

        # Test slug or name integrity violation
        with testtools.ExpectedException(exc.Duplicate):
            info = {
                'name': 'my domain'
            }
            api.domain_update(ctx, d2_id, info, session=self.sess)

        spec = fakes.get_search_spec()
        domains = api.domains_get(ctx, spec, session=self.sess)
        self.assertThat(domains, matchers.HasLength(2))

        spec = fakes.get_search_spec(filters=dict(ownerId=u_id))
        domains = api.domains_get(ctx, spec, session=self.sess)
        self.assertThat(domains, matchers.HasLength(1))
        tmp_d = domains[0]
        self.assertEquals(d, tmp_d)

        api.domain_delete(ctx, d_id, session=self.sess)

        spec = fakes.get_search_spec(filters=dict(ownerId=u_id))
        domains = api.domains_get(ctx, spec, session=self.sess)
        self.assertThat(domains, matchers.HasLength(0))

        spec = fakes.get_search_spec(filters=dict(ownerId=u2_id))
        domains = api.domains_get(ctx, spec, session=self.sess)
        self.assertThat(domains, matchers.HasLength(1))

        # Test transferring ownership
        info = {
            'ownerId': u_id  # was u2_id
        }
        api.domain_update(ctx, d2_id, info, session=self.sess)

        spec = fakes.get_search_spec(filters=dict(ownerId=u2_id))
        domains = api.domains_get(ctx, spec, session=self.sess)
        self.assertThat(domains, matchers.HasLength(0))

        spec = fakes.get_search_spec(filters=dict(ownerId=u_id))
        domains = api.domains_get(ctx, spec, session=self.sess)
        self.assertThat(domains, matchers.HasLength(1))

    def test_domain_update_not_found(self):
        ctx = mock.Mock()
        with testtools.ExpectedException(exc.NotFound):
            api.domain_update(ctx, fakes.NO_EXIST_UUID, {}, session=self.sess)

    def test_repo_get_by_pk_not_found(self):
        ctx = mock.Mock()
        with testtools.ExpectedException(exc.NotFound):
            api.repo_get_by_pk(ctx, fakes.NO_EXIST_UUID, session=self.sess)

    def test_repo_create_owner_domain_not_found(self):
        ctx = mock.Mock()

        info = {
            'name': 'user 1',
            'email': 'user1@example.com'
        }
        u = api.user_create(ctx, info, session=self.sess)
        u_id = u.id
        self.addCleanup(api.user_delete, ctx, u_id, session=self.sess)

        info = {
            'name': 'my domain',
            'ownerId': u_id
        }
        d = api.domain_create(ctx, info, session=self.sess)
        d_id = d.id
        self.addCleanup(api.domain_delete, ctx, d_id, session=self.sess)

        info = {'name': 'my repo',
                'domainId': d_id,
                'ownerId': fakes.NO_EXIST_UUID}
        with testtools.ExpectedException(exc.NotFound):
            api.repo_create(ctx, info, session=self.sess)

        info = {'name': 'my repo',
                'domainId': fakes.NO_EXIST_UUID,
                'ownerId': u_id}
        with testtools.ExpectedException(exc.NotFound):
            api.repo_create(ctx, info, session=self.sess)

    def test_repo_delete_exceptions(self):
        ctx = mock.Mock()
        with testtools.ExpectedException(exc.NotFound):
            api.repo_delete(ctx, fakes.NO_EXIST_UUID, session=self.sess)

    def test_repo_crud(self):
        ctx = mock.Mock()
        info = {
            'name': 'user 1',
            'email': 'user1@example.com'
        }
        u = api.user_create(ctx, info, session=self.sess)
        u_id = u.id
        self.addCleanup(api.user_delete, ctx, u_id, session=self.sess)

        info = {
            'name': 'user 2',
            'email': 'user2@example.com'
        }
        u2 = api.user_create(ctx, info, session=self.sess)
        u2_id = u2.id
        self.addCleanup(api.user_delete, ctx, u2_id, session=self.sess)

        info = {
            'name': 'my domain',
            'ownerId': u_id
        }
        d = api.domain_create(ctx, info, session=self.sess)
        d_id = d.id
        self.addCleanup(api.domain_delete, ctx, d_id, session=self.sess)

        info = {
            'name': 'my domain 2',
            'ownerId': u2_id
        }
        d2 = api.domain_create(ctx, info, session=self.sess)
        d2_id = d2.id
        # We don't add a cleanup here because we manually delete this
        # domain below when testing for cascading deletes.

        info = {
            'name': 'my repo',
            'domainId': d_id,
            'ownerId': u_id
        }
        r = api.repo_create(ctx, info, session=self.sess)
        r_id = r.id

        with testtools.ExpectedException(exc.Duplicate):
            api.repo_create(ctx, info, session=self.sess)

        self.assertEquals(r.name, info['name'])

        r2 = api.repo_get_by_pk(ctx, r_id, session=self.sess)
        self.assertEquals(r, r2)

        info = {
            'name': 'my repo 2',
            'domainId': d_id,
            'ownerId': u2_id
        }
        r2 = api.repo_create(ctx, info, session=self.sess)
        r2_id = r2.id
        # We don't add a cleanup for these repositories because we
        # expect that deleting the domain below will delete the child
        # repositories.

        info = {
            'name': 'foo repo 2'
        }
        tmp_r = api.repo_update(ctx, r2_id, info, session=self.sess)
        self.assertEquals(info['name'], tmp_r.name)
        self.assertEquals(u2_id, tmp_r.ownerId)

        # Can't update domainId to a non-existing user or None
        with testtools.ExpectedException(exc.NotFound):
            info = {
                'domainId': fakes.NO_EXIST_UUID
            }
            api.repo_update(ctx, r2_id, info, session=self.sess)

        # Can't update ownerId to a non-existing user or None
        with testtools.ExpectedException(exc.NotFound):
            info = {
                'ownerId': fakes.NO_EXIST_UUID
            }
            api.repo_update(ctx, r2_id, info, session=self.sess)

        # Test name integrity violation within same domain
        with testtools.ExpectedException(exc.Duplicate):
            info = {
                'name': 'my repo'
            }
            api.repo_update(ctx, r2_id, info, session=self.sess)

        # Test that we *can* update the repo to the same
        # name as another repo if we also update the domainId
        info = {
            'name': 'my repo',
            'domainId': d2_id
        }
        tmp_r2 = api.repo_update(ctx, r2_id, info, session=self.sess)
        self.assertEquals(r2.ownerId, tmp_r2.ownerId)
        self.assertEquals(d2_id, tmp_r2.domainId)

        spec = fakes.get_search_spec()
        repos = api.repos_get(ctx, spec, session=self.sess)
        self.assertThat(repos, matchers.HasLength(2))

        spec = fakes.get_search_spec(filters=dict(ownerId=u_id))
        repos = api.repos_get(ctx, spec, session=self.sess)
        self.assertThat(repos, matchers.HasLength(1))
        tmp_r = repos[0]
        self.assertEquals(r, tmp_r)

        api.repo_delete(ctx, r_id, session=self.sess)

        spec = fakes.get_search_spec(filters=dict(ownerId=u_id))
        repos = api.repos_get(ctx, spec, session=self.sess)
        self.assertThat(repos, matchers.HasLength(0))

        spec = fakes.get_search_spec(filters=dict(ownerId=u2_id))
        repos = api.repos_get(ctx, spec, session=self.sess)
        self.assertThat(repos, matchers.HasLength(1))

        # Test transferring ownership
        info = {
            'ownerId': u_id  # was u2_id
        }
        api.repo_update(ctx, r2_id, info, session=self.sess)

        spec = fakes.get_search_spec(filters=dict(ownerId=u2_id))
        repos = api.repos_get(ctx, spec, session=self.sess)
        self.assertThat(repos, matchers.HasLength(0))

        spec = fakes.get_search_spec(filters=dict(ownerId=u_id))
        repos = api.repos_get(ctx, spec, session=self.sess)
        self.assertThat(repos, matchers.HasLength(1))

        # Test the helper method that returns repos for a domain
        spec = fakes.get_search_spec()
        repos = api.domain_repos_get(ctx, d2_id, spec, session=self.sess)
        self.assertThat(repos, matchers.HasLength(1))

        # Same method should work the same passing the domain's slug
        # instead of the primary key
        repos = api.domain_repos_get(ctx, d2.slug, spec, session=self.sess)
        self.assertThat(repos, matchers.HasLength(1))

        # Test the helper method that returns a single repo given
        # an ID or slug for domain and an ID or name for repo
        tmp_repo = api.domain_repo_get_by_name(ctx, d2_id, 'my repo',
                                               session=self.sess)
        self.assertEquals(tmp_repo, r2)
        tmp_repo = api.domain_repo_get_by_name(ctx, d2_id, r2_id,
                                               session=self.sess)
        self.assertEquals(tmp_repo, r2)
        with testtools.ExpectedException(exc.NotFound):
            api.domain_repo_get_by_name(ctx, d2_id, 'my nonexisting',
                                        session=self.sess)
        with testtools.ExpectedException(exc.NotFound):
            api.domain_repo_get_by_name(ctx, 'nonexisting', 'my repo',
                                        session=self.sess)

        # Test deleting the domain removes any repositories under
        # that domain.
        api.domain_delete(ctx, d2_id, session=self.sess)

        spec = fakes.get_search_spec()
        repos = api.repos_get(ctx, spec, session=self.sess)
        self.assertThat(repos, matchers.HasLength(0))

    def test_repo_update_not_found(self):
        ctx = mock.Mock()
        with testtools.ExpectedException(exc.NotFound):
            api.repo_update(ctx, fakes.NO_EXIST_UUID, {}, session=self.sess)

    def test_changeset_get_by_pk_not_found(self):
        ctx = mock.Mock()
        with testtools.ExpectedException(exc.NotFound):
            api.changeset_get_by_pk(ctx, fakes.NO_EXIST_UUID, session=self.sess)

    def test_changeset_create_uploadedBy_repo_not_found(self):
        ctx = mock.Mock()

        info = {
            'name': 'user 1',
            'email': 'user1@example.com'
        }
        u = api.user_create(ctx, info, session=self.sess)
        u_id = u.id
        self.addCleanup(api.user_delete, ctx, u_id, session=self.sess)

        info = {
            'name': 'my domain',
            'ownerId': u_id
        }
        d = api.domain_create(ctx, info, session=self.sess)
        d_id = d.id
        self.addCleanup(api.domain_delete, ctx, d_id, session=self.sess)

        info = {
            'name': 'my repo',
            'domainId': d_id,
            'ownerId': u_id
        }
        r = api.repo_create(ctx, info, session=self.sess)
        r_id = r.id
        self.addCleanup(api.repo_delete, ctx, r_id, session=self.sess)

        info = {'targetRepoId': fakes.NO_EXIST_UUID,
                'targetBranch': 'blah',
                'uploadedBy': u_id,
                'commitMessage': ''}
        with testtools.ExpectedException(exc.NotFound):
            api.changeset_create(ctx, info, session=self.sess)

        info = {'targetRepoId': r_id,
                'targetBranch': 'blah',
                'uploadedBy': fakes.NO_EXIST_UUID,
                'commitMessage': ''}
        with testtools.ExpectedException(exc.NotFound):
            api.changeset_create(ctx, info, session=self.sess)

    def test_changeset_create_bad_data(self):
        ctx = mock.Mock()
        e_mock = self.patch('procession.db.api._exists')
        e_mock.return_value = True
        info = {}
        with testtools.ExpectedException(ValueError):
            api.changeset_create(ctx, info)

        # Missing uploaded by
        info = {
            'targetRepoId': 'blah',
            'targetBranch': 'blah',
            'commitMessage': 'blah',
        }
        with testtools.ExpectedException(ValueError):
            api.changeset_create(ctx, info)

        # Missing target branch
        info = {
            'targetRepoId': 'blah',
            'uploadedBy': 'blah',
            'commitMessage': 'blah',
        }
        with testtools.ExpectedException(ValueError):
            api.changeset_create(ctx, info)

        # Missing target repo
        info = {
            'targetBranch': 'blah',
            'uploadedBy': 'blah',
            'commitMessage': 'blah',
        }
        with testtools.ExpectedException(ValueError):
            api.changeset_create(ctx, info)

        # Missing commit message
        info = {
            'targetRepoId': 'blah',
            'targetBranch': 'blah',
            'uploadedBy': 'blah',
        }
        with testtools.ExpectedException(ValueError):
            api.changeset_create(ctx, info)

    def test_changeset_delete_exceptions(self):
        ctx = mock.Mock()
        with testtools.ExpectedException(exc.NotFound):
            api.changeset_delete(ctx, fakes.NO_EXIST_UUID, session=self.sess)

    def test_changeset_crud(self):
        ctx = mock.Mock()
        info = {
            'name': 'user 1',
            'email': 'user1@example.com'
        }
        u = api.user_create(ctx, info, session=self.sess)
        u_id = u.id
        self.addCleanup(api.user_delete, ctx, u_id, session=self.sess)

        info = {
            'name': 'my domain',
            'ownerId': u_id
        }
        d = api.domain_create(ctx, info, session=self.sess)
        d_id = d.id
        self.addCleanup(api.domain_delete, ctx, d_id, session=self.sess)

        info = {
            'name': 'my repo',
            'domainId': d_id,
            'ownerId': u_id
        }
        r = api.repo_create(ctx, info, session=self.sess)
        r_id = r.id

        info = {
            'targetRepoId': r_id,
            'targetBranch': 'blah',
            'uploadedBy': u_id,
            'commitMessage': 'my commit message'
        }
        c = api.changeset_create(ctx, info, session=self.sess)
        c_id = c.id

        spec = fakes.get_search_spec()
        csets = api.changesets_get(ctx, spec, session=self.sess)
        self.assertThat(csets, matchers.HasLength(1))

        api.changeset_delete(ctx, c_id, session=self.sess)

        spec = fakes.get_search_spec()
        csets = api.changesets_get(ctx, spec, session=self.sess)
        self.assertThat(csets, matchers.HasLength(0))
