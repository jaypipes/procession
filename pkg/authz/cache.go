package authz

import (
    "time"

    "github.com/jaypipes/procession/pkg/iam/iamstorage"
    pb "github.com/jaypipes/procession/proto"
)

type cacheEntry struct {
    perms *pb.Permissions
    expires time.Time
}

type PermissionsCache struct {
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
        return nil
    }
    if now.After(entry.expires) {
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
        perms = &pb.Permissions{
            System: &pb.PermissionSet{
                Permissions: []pb.Permission{},
            },
        }
    } else {
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
