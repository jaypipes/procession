package authz

import (
    "testing"

    pb "github.com/jaypipes/procession/proto"
)

func TestCheckSuper(t *testing.T) {
    perms := &pb.Permissions{
        Permissions: []pb.Permission{
            pb.Permission_SUPER,
        },
    }
    ctx := &Context{
        permissions: perms,
    }
    authz := &Authz{}

    failIfNot := func (p pb.Permission) {
        if ! authz.Check(ctx, p) {
            t.Fatalf(
                "Expected check of %v with perms %v to succeed.",
                p,
                perms.Permissions,
            )
        }
    }

    failIfNot(pb.Permission_READ_ANY)
    failIfNot(pb.Permission_READ_ORGANIZATION)
    failIfNot(pb.Permission_DELETE_USER)
    failIfNot(pb.Permission_MODIFY_CHANGE)
}

func TestCheckReadAny(t *testing.T) {
    perms := &pb.Permissions{
        Permissions: []pb.Permission{
            pb.Permission_READ_ANY,
        },
    }
    ctx := &Context{
        permissions: perms,
    }
    authz := &Authz{}

    failIf := func (p pb.Permission, expect bool) {
        if authz.Check(ctx, p) != expect {
            t.Fatalf(
                "Expected check of %v with perms %v to be %v.",
                p,
                perms.Permissions,
                expect,
            )
        }
    }

    failIf(pb.Permission_READ_ORGANIZATION, true)
    failIf(pb.Permission_READ_USER, true)
    failIf(pb.Permission_DELETE_USER, false)
    failIf(pb.Permission_MODIFY_CHANGE, false)
    failIf(pb.Permission_SUPER, false)
}

func TestCheckReadUser(t *testing.T) {
    perms := &pb.Permissions{
        Permissions: []pb.Permission{
            pb.Permission_READ_USER,
        },
    }
    ctx := &Context{
        permissions: perms,
    }
    authz := &Authz{}

    failIf := func (p pb.Permission, expect bool) {
        if authz.Check(ctx, p) != expect {
            t.Fatalf(
                "Expected check of %v with perms %v to be %v.",
                p,
                perms.Permissions,
                expect,
            )
        }
    }

    failIf(pb.Permission_READ_USER, true)
    failIf(pb.Permission_READ_ORGANIZATION, false)
    failIf(pb.Permission_DELETE_USER, false)
    failIf(pb.Permission_MODIFY_CHANGE, false)
    failIf(pb.Permission_SUPER, false)
}

func TestIsRead(t *testing.T) {
    good := []pb.Permission{
        pb.Permission_READ_ANY,
        pb.Permission_READ_ORGANIZATION,
        pb.Permission_READ_USER,
        pb.Permission_READ_REPO,
        pb.Permission_READ_CHANGESET,
        pb.Permission_READ_CHANGE,
    }

    for _, p := range good {
        if ! isRead(p) {
            t.Fatalf("Permission %v should be a read permission", p)
        }
    }

    bad := []pb.Permission{
        pb.Permission_CREATE_ANY,
        pb.Permission_DELETE_ORGANIZATION,
        pb.Permission_MODIFY_USER,
    }

    for _, p := range bad {
        if isRead(p) {
            t.Fatalf("Permission %v should NOT be a read permission", p)
        }
    }
}

func TestIsCreate(t *testing.T) {
    good := []pb.Permission{
        pb.Permission_CREATE_ANY,
        pb.Permission_CREATE_ORGANIZATION,
        pb.Permission_CREATE_USER,
        pb.Permission_CREATE_REPO,
        pb.Permission_CREATE_CHANGESET,
        pb.Permission_CREATE_CHANGE,
    }

    for _, p := range good {
        if ! isCreate(p) {
            t.Fatalf("Permission %v should be a create permission", p)
        }
    }

    bad := []pb.Permission{
        pb.Permission_READ_ANY,
        pb.Permission_DELETE_ORGANIZATION,
        pb.Permission_MODIFY_USER,
    }

    for _, p := range bad {
        if isCreate(p) {
            t.Fatalf("Permission %v should NOT be a create permission", p)
        }
    }
}

func TestIsModify(t *testing.T) {
    good := []pb.Permission{
        pb.Permission_MODIFY_ANY,
        pb.Permission_MODIFY_ORGANIZATION,
        pb.Permission_MODIFY_USER,
        pb.Permission_MODIFY_REPO,
        pb.Permission_MODIFY_CHANGESET,
        pb.Permission_MODIFY_CHANGE,
    }

    for _, p := range good {
        if ! isModify(p) {
            t.Fatalf("Permission %v should be a modify permission", p)
        }
    }

    bad := []pb.Permission{
        pb.Permission_CREATE_ANY,
        pb.Permission_READ_ORGANIZATION,
        pb.Permission_DELETE_USER,
    }

    for _, p := range bad {
        if isModify(p) {
            t.Fatalf("Permission %v should NOT be a modify permission", p)
        }
    }
}

func TestIsDelete(t *testing.T) {
    good := []pb.Permission{
        pb.Permission_DELETE_ANY,
        pb.Permission_DELETE_ORGANIZATION,
        pb.Permission_DELETE_USER,
        pb.Permission_DELETE_REPO,
        pb.Permission_DELETE_CHANGESET,
        pb.Permission_DELETE_CHANGE,
    }

    for _, p := range good {
        if ! isDelete(p) {
            t.Fatalf("Permission %v should be a delete permission", p)
        }
    }

    bad := []pb.Permission{
        pb.Permission_CREATE_ANY,
        pb.Permission_READ_ORGANIZATION,
        pb.Permission_MODIFY_USER,
    }

    for _, p := range bad {
        if isDelete(p) {
            t.Fatalf("Permission %v should NOT be a delete permission", p)
        }
    }
}
