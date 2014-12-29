@0x9fb4b7a5131ac08f;
# The world-view of Procession is divided into Organizations,
# Users, and Groups. Organizations are simply containers for Users and other
# Organizations. Groups are containers for Users within an Organization that
# are used for simple categorization of Users. Groups have a set of Roles
# associated with them, and Roles are used to indicate the permissions that
# Users in the Group having that Role are assigned.
# 
# Organizations that have no parent Organization are known as Root
# Organizations. Each Organization has attributes for both a Parent
# Organization as well as the Root Organization to which the Organization
# belongs. This allows us to use both an adjacency list model for quick
# immediate ancestor and immediate descendant queries, as well as a nested
# sets model for more complex queries involving multiple levels of the
# Organization hierarchy.
# 
# We use multiple Root Organizations in order to minimize the impact of
# updates to the Organization hierarchy. Since updating a nested sets model
# is expensive -- since every node in the hierarchy must be updated to
# change the left and right side pointer values -- dividing the whole
# Organization hierarchy into multiple roots allows us to have a nested set
# model per Root Organization, which limits updates to just the Organizations
# within a Root Organization. If we used a single-root tree, with all
# Organizations descendents from a single Organization with no parent, then
# each addition or removal of an Organization would result in the need to
# update every record in the organizations table.

struct Organization {
  id @0 :Data;
  # Unique identifier for this organization. This is a UUID identifier.

  name @1 :Text;
  # User-defined unique name for this organization

  slug @2 :Text;
  # Stripped-down, generated slug from the name

  createdOn @3 :Text;
  # Timestamp of when the organization was created

  rootOrganizationId @4 :Data;
  # Identifier of the root organization this organization belongs to. Note that
  # an organization can only belong to a single root organization, but that
  # that there can be many root organizations -- i.e. there is not a single,
  # large organization tree. If this organization is the root of an
  # organization tree, this value will be the same as the id field.

  parentOrganizationId @5 :Data;
  # Either void, or the identifier of the immediate parent organization.
  # Mostly used for adjacency list querying of the organizations.

  leftSequence @6 :UInt64;
  # The nested sets modeling left value for the organization.

  rightSequence @7 :UInt64;
  # The nested sets modeling right value for the organization.
}
