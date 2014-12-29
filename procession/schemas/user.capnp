@0x9e1eb453d8c9f2bd;

using Group = import "group.capnp".Group;
using UserPublicKey = import "user_public_key.capnp".UserPublicKey;

struct User {
  id @0 :Data;
  # Unique identifier for this user. This is a UUID identifier.

  name @1 :Text;
  # User-defined unique name for this user

  slug @2 :Text;
  # Stripped-down, generated slug from the name

  createdOn @3 :Text;
  # Timestamp of when the user was created

  email @4 :Text;
  # Email address of the user

  groups @5 :List(Group);

  publicKeys @6 :List(UserPublicKey);
}
