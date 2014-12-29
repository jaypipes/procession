@0xa00c7eb6704a319c;

struct Changeset {
  enum State {
    abandoned @0;  # The changeset has been abandoned by the original uploader.
    draft @1;      # The changeset is a work in progress.
    active @2;     # The changeset is ready for reviews.
    cleared @3;    # The changeset has been cleared for gate checks.
    merged @4;     # The changeset was merged into its target branch.
  }

  id @0 :Data;
  # Unique identifier for this changeset. This is a SHA1 identifier.

  targetRepoId @1 :Data;
  # Identifier for the target repository.

  targetBranch @2 :Text;
  # The SCM target branch that this changeset would be applied to.

  createdOn @3 :Text;
  # Timestamp of when the changeset was created.

  uploadedBy @4 :Data;
  # Identifier for the user who uploaded the first change in the changeset.

  commitMessage @5 :Text;
  # The commit message to be used for the final merge commit.

  state @6 :State;
  # The state of the changeset as a whole.
}
