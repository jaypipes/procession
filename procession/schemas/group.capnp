@0xa501bfd078efaa73;

struct Group {
  id @0 :Data;
  # Unique identifier for this group. This is a UUID identifier.

  name @1 :Text;
  # User-defined unique name for this group

  slug @2 :Text;
  # Stripped-down, generated slug from the name

  createdOn @3 :Text;
  # Timestamp of when the group was created

  rootOrganizationId @4 :Data;
  # Identifier of the root organization this group belongs to.
}
