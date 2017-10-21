package authz

import (
	"testing"

	pb "github.com/jaypipes/procession/proto"
)

var (
	stubSession = &pb.Session{
		User: "user-id",
	}
)

type lookupFixture struct {
	perms []pb.Permission
}

func (c *lookupFixture) Get(sess *pb.Session) *pb.UserPermissions {
	return &pb.UserPermissions{
		System: &pb.PermissionSet{
			Permissions: c.perms,
		},
	}
}

func authFixture(perms ...pb.Permission) *Authz {
	return &Authz{
		lookup: &lookupFixture{
			perms: perms,
		},
	}
}

func failIfNot(t *testing.T, authz *Authz, p pb.Permission, expect bool) {
	if authz.Check(stubSession, p) != expect {
		t.Fatalf(
			"Expected check of %v with perms %v to be %v.",
			p,
			authz.lookup.Get(stubSession),
			expect,
		)
	}
}

func failIfNotAll(t *testing.T, authz *Authz, p []pb.Permission, expect bool) {
	if authz.CheckAll(stubSession, p...) != expect {
		t.Fatalf(
			"Expected check all of %v with perms %v to be %v.",
			p,
			authz.lookup.Get(stubSession),
			expect,
		)
	}
}

func TestCheckSuper(t *testing.T) {
	authz := authFixture(pb.Permission_SUPER)

	failIfNot(t, authz, pb.Permission_READ_ANY, true)
	failIfNot(t, authz, pb.Permission_READ_ORGANIZATION, true)
	failIfNot(t, authz, pb.Permission_DELETE_USER, true)
	failIfNot(t, authz, pb.Permission_MODIFY_CHANGE, true)
}

func TestCheckReadAny(t *testing.T) {
	authz := authFixture(pb.Permission_READ_ANY)

	failIfNot(t, authz, pb.Permission_READ_ORGANIZATION, true)
	failIfNot(t, authz, pb.Permission_READ_USER, true)
	failIfNot(t, authz, pb.Permission_DELETE_USER, false)
	failIfNot(t, authz, pb.Permission_MODIFY_CHANGE, false)
	failIfNot(t, authz, pb.Permission_SUPER, false)
}

func TestCheckReadUser(t *testing.T) {
	authz := authFixture(pb.Permission_READ_USER)

	failIfNot(t, authz, pb.Permission_READ_ORGANIZATION, false)
	failIfNot(t, authz, pb.Permission_READ_USER, true)
	failIfNot(t, authz, pb.Permission_DELETE_USER, false)
	failIfNot(t, authz, pb.Permission_MODIFY_CHANGE, false)
	failIfNot(t, authz, pb.Permission_SUPER, false)
}

func TestCheckAll(t *testing.T) {
	authz := authFixture(
		pb.Permission_READ_ANY,
		pb.Permission_DELETE_ORGANIZATION,
	)

	failIfNotAll(t, authz, []pb.Permission{pb.Permission_READ_ORGANIZATION, pb.Permission_DELETE_USER}, false)
	failIfNotAll(t, authz, []pb.Permission{pb.Permission_READ_USER, pb.Permission_DELETE_ORGANIZATION}, true)
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
		if !isRead(p) {
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
		if !isCreate(p) {
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
		if !isModify(p) {
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
		if !isDelete(p) {
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
