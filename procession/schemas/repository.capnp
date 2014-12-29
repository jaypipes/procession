@0xf292dcfc1e309844;

struct Repository {
  id @0 :Data;
  # Unique identifier for this repository. This is a UUID identifier.

  name @1 :Text;
  # User-defined unique name for this repository.

  slug @2 :Text;
  # Stripped-down, generated slug from the name.

  createdOn @3 :Text;
  # Timestamp of when the repository was created.

  ownerId @4 :Data;
  # Identifier for the owner of the repository.

  domainId @5 :Data;
  # Identifier for the domain that contains the repository.
}
