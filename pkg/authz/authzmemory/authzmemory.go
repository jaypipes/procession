package authzmemory

import (
    "time"

    "github.com/jaypipes/procession/pkg/authz"
    "github.com/jaypipes/procession/pkg/errors"
    "github.com/jaypipes/procession/pkg/iam/iamstorage"
    "github.com/jaypipes/procession/pkg/logging"
    pb "github.com/jaypipes/procession/proto"
)

// Simple wrapper struct that tacks on an expiry time for eviction
type entry struct {
    perms *pb.UserPermissions
    expires time.Time
}

type lookup struct {
    log *logging.Logs
    // Map, keyed by session user identifier, of the user's known permissions
    pmap map[string]*entry
    // Storage interface for loading roles for a user
    storage *iamstorage.IAMStorage
}

// Returns an authz.Authz concrete struct that loads user information from the
// supplied storage interface and stores this user information in memory
func New(
    log *logging.Logs,
    storage *iamstorage.IAMStorage,
) (*authz.Authz, error) {
    entries := make(map[string]*entry, 0)
    lu := &lookup{
        log: log,
        pmap: entries,
        storage: storage,
    }
    return authz.New(log, lu)
}

func (lu *lookup) Get(
    sess *pb.Session,
) (*pb.UserPermissions) {
    defer lu.log.WithSection("authz/authzmemory")()

    now := time.Now()
    entry, found := lu.pmap[sess.User]
    if ! found {
        entry = lu.load(sess.User)
        if entry != nil {
            return entry.perms
        }
        return nil
    }
    if now.After(entry.expires) {
        lu.log.L3(
            "evicting expired permissions cached for user %s",
            sess.User,
        )
        delete(lu.pmap, sess.User)
        entry = lu.load(sess.User)
    }
    return entry.perms
}

func (lu *lookup) load(user string) *entry {
    defer lu.log.WithSection("authz/authzmemory")()

    // load the user's permissions from backend storage
    perms, err := lu.storage.UserPermissionsGet(user)
    if err != nil {
        if ! errors.IsNotFound(err) {
            lu.log.ERR(
                "error attempting to retrieve permissions for user %s: %v",
                user,
                err,
            )
        }
        return nil
    } else {
        lu.log.L3(
            "permissions loaded for user %s: %v",
            user,
            perms,
        )
    }

    expires := time.Now().Add(time.Duration(15 * time.Minute))
    entry := &entry{
        perms: perms,
        expires: expires,
    }
    lu.pmap[user] = entry
    return entry
}
