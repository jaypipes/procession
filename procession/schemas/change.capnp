@0x9b8154ac136a3e44;

struct Change {
  changesetId @0 :Data;
  # Identifier for this changeset. This is a SHA1 identifier.

  sequence @1 :UInt16;
  # Ordinal sequence of this change within the changeset.

  createdOn @2 :Text;
  # Timestamp of when the change was created.

  uploadedBy @3 :Data;
  # Identifier for the user who uploaded this change in the changeset.
}
