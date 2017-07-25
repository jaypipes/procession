package authz

import (
    "github.com/jaypipes/procession/pkg/logging"
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

// Abstraction layer for authorization implementations
type AuthzLookup interface {
    Get(*pb.Session) (*pb.UserPermissions)
}

type Authz struct {
    log *logging.Logs
    lookup AuthzLookup
}

func New(log *logging.Logs, lookup AuthzLookup) (*Authz, error) {
    authz := &Authz{
        log: log,
        lookup: lookup,
    }
    return authz, nil
}

func (a *Authz) sessionPermissions(
    sess *pb.Session,
) (*pb.UserPermissions) {
    if a.lookup == nil {
        return nil
    }
    return a.lookup.Get(sess)
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

// Checks that the user in the supplied session object has permission to
// perform all supplied actions
func (a *Authz) CheckAll(
    sess *pb.Session,
    checked ...pb.Permission,
) bool {
    res := true
    for _, check := range checked {
        res = res && a.Check(sess, check)
    }
    return res
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
