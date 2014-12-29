@0xa869ac2a0cd021e6;

struct UserPublicKey {
  userId @0 :Data;
  # Unique identifier for this user. This is a UUID identifier.

  fingerprint @1 :Text;
  # Fingerprint of the SSH public Key

  publicKey @2 :Text;
  # Text value of the SSH public key

  createdOn @3 :Text;
  # Timestamp of when the public key was created
}
