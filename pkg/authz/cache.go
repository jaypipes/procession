package authz

import (
    "time"

    "github.com/jaypipes/procession/pkg/storage"
    "github.com/jaypipes/procession/pkg/iam/iamstorage"
    "github.com/jaypipes/procession/pkg/logging"
    pb "github.com/jaypipes/procession/proto"
)

type cacheEntry struct {
    perms *pb.Permissions
    expires time.Time
}

type PermissionsCache struct {
    log *logging.Logs
    // Map, keyed by user UUID, of the user's known permissions
    pmap map[string]*cacheEntry
    // Storage interface for loading roles for a user
    storage *iamstorage.IAMStorage
}

func (pc *PermissionsCache) get(
    sess *pb.Session,
) (*pb.Permissions) {
    now := time.Now()
    entry := pc.find(sess.User)
    if entry == nil {
        entry = pc.load(sess.User)
        if entry != nil {
            return entry.perms
        }
        return nil
    }
    if now.After(entry.expires) {
        pc.log.L3(
            "evicting expired permissions cached for user %s",
            sess.User,
        )
        delete(pc.pmap, sess.User)
        entry = pc.load(sess.User)
    }
    return entry.perms
}

func (pc *PermissionsCache) find(user string) *cacheEntry {
    for key, value := range pc.pmap {
        if key == user {
            return value
        }
    }
    return nil
}

func (pc *PermissionsCache) load(user string) *cacheEntry {
    // load the user's permissions from backend storage
    sysPerms, err := pc.storage.UserSystemPermissions(user)
    var perms *pb.Permissions
    if err != nil {
        if err != storage.ERR_NOTFOUND_USER {
            pc.log.ERR(
                "error attempting to retrieve permissions for user %s: %v",
                user,
                err,
            )
        }
        return nil
    } else {
        pc.log.L3(
            "permissions loaded for user %s: %v",
            user,
            sysPerms,
        )
        perms = &pb.Permissions{
            System: &pb.PermissionSet{
                Permissions: sysPerms,
            },
        }
    }

    expires := time.Now().Add(time.Duration(15 * time.Minute))
    entry := &cacheEntry{
        perms: perms,
        expires: expires,
    }
    pc.pmap[user] = entry
    return entry
}
