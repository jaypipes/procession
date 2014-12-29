@0xdf621a155adb9eb6;
using Repository = import "repository.capnp".Repository;

struct Domain {

  enum Visibility {
      all @0; # Visible to anyone.
      restricted @1; # Only visible to a subset of users or groups.
  }

  id @0 :Data;
  # Unique identifier for this domain. This is a UUID identifier.

  name @1 :Text;
  # User-defined unique name for this domain.

  slug @2 :Text;
  # Stripped-down, generated slug from the name.

  createdOn @3 :Text;
  # Timestamp of when the domain was created.

  ownerId @4 :Data;
  # Identifier for the owner of the domain.

  visibility @5 :Visibility;
  # Who can see the repository

  repositories @6 :List(Repository);
}
