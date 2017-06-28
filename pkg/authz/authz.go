package authz

import (
    pb "github.com/jaypipes/procession/proto"
)

const (
    readPermsStart = pb.Permission_READ_ANY
    readPermsEnd = (pb.Permission_CREATE_ANY - 1)
    createPermsStart = pb.Permission_CREATE_ANY
    createPermsEnd = (pb.Permission_MODIFY_ANY - 1)
    modifyPermsStart = pb.Permission_MODIFY_ANY
    modifyPermsEnd = (pb.Permission_DELETE_ANY - 1)
    deletePermsStart = pb.Permission_DELETE_ANY
    deletePermsEnd = pb.Permission_END_PERMS
)

type PermissionsGetter interface {
    get(*pb.Session) (*pb.Permissions)
}

type Authz struct {
    cache PermissionsGetter
}

func New() (*Authz, error) {
    authz := &Authz{}
    return authz, nil
}

func (a *Authz) sessionPermissions(
    sess *pb.Session,
) (*pb.Permissions) {
    return a.cache.get(sess)
}

// Simple check that the user in the supplied session object has permission to
// perform the action
func (a *Authz) Check(
    sess *pb.Session,
    checked pb.Permission,
) bool {
    sessPerms := a.sessionPermissions(sess)
    if sessPerms == nil {
        return false
    }
    perms := sessPerms.System.Permissions
    find := []pb.Permission{
        pb.Permission_SUPER,  // SUPER permission is allowed to do anything...
        checked,
    }

    if isRead(checked) {
        find = append(find, pb.Permission_READ_ANY)
    } else if isCreate(checked) {
        find = append(find, pb.Permission_CREATE_ANY)
    } else if isModify(checked) {
        find = append(find, pb.Permission_MODIFY_ANY)
    } else if isDelete(checked) {
        find = append(find, pb.Permission_DELETE_ANY)
    }

    return hasAny(perms, find)
}

func isRead(check pb.Permission) bool {
    return check >= readPermsStart && check <= readPermsEnd
}

func isCreate(check pb.Permission) bool {
    return check >= createPermsStart && check <= createPermsEnd
}

func isModify(check pb.Permission) bool {
    return check >= modifyPermsStart && check <= modifyPermsEnd
}

func isDelete(check pb.Permission) bool {
    return check >= deletePermsStart && check <= deletePermsEnd
}

// Returns true if any of the searched-for permissions are contained in the
// subject permissions
func hasAny(perms []pb.Permission, find []pb.Permission) bool {
    for _, p := range perms {
        for _, f := range find {
            if p == f {
                return true
            }
        }
    }
    return false
}
