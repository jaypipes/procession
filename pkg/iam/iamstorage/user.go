package iamstorage

import (
    "fmt"
    "database/sql"
    "strings"

    "github.com/gosimple/slug"
    "github.com/jaypipes/sqlb"

    "github.com/jaypipes/procession/pkg/errors"
    "github.com/jaypipes/procession/pkg/sqlutil"
    "github.com/jaypipes/procession/pkg/storage"
    "github.com/jaypipes/procession/pkg/util"
    pb "github.com/jaypipes/procession/proto"
)

var (
    userSortFields = []*sqlutil.SortFieldInfo{
        &sqlutil.SortFieldInfo{
            Name: "uuid",
            Unique: true,
        },
        &sqlutil.SortFieldInfo{
            Name: "email",
            Unique: true,
        },
        &sqlutil.SortFieldInfo{
            Name: "display_name",
            Unique: false,
            Aliases: []string{
                "name",
                "display name",
                "display_name",
            },
        },
    }
)

// A generator that returns a function that returns a string value of a sort
// field after looking up an user by UUID
func (s *IAMStorage) userSortFieldByUuid(
    uuid string,
    sortField *pb.SortField,
) func () string {
    f := func () string {
        qs := fmt.Sprintf(
            "SELECT %s FROM users WHERE uuid = ?",
            sortField.Field,
        )
        qargs := []interface{}{uuid}
        rows, err := s.Rows(qs, qargs...)
        if err != nil {
            return ""
        }
        defer rows.Close()
        var sortVal string
        for rows.Next() {
            err = rows.Scan(&sortVal)
            if err != nil {
                return ""
            }
            return sortVal
        }
        return ""
    }
    return f
}

// Simple wrapper struct that allows us to pass the internal ID for a
// user around with a protobuf message of the external representation
// of the user
type userRecord struct {
    pb *pb.User
    id int64
}

// Returns a sql.Rows yielding users matching a set of supplied filters
func (s *IAMStorage) UserList(
    req *pb.UserListRequest,
) (storage.RowIterator, error) {
    filters := req.Filters
    opts := req.Options
    err := sqlutil.NormalizeSortFields(opts, &userSortFields)
    if err != nil {
        return nil, err
    }
    qs := `
SELECT
  u.uuid
, u.email
, u.display_name
, u.slug
, u.generation
FROM users AS u
`
    qargs := make([]interface{}, 0)
    if filters.Identifiers != nil {
        qs = qs + "WHERE ("
        for x, search := range filters.Identifiers {
            orStr := ""
            if x > 0 {
                orStr = "\nOR "
            }
            colName := "u.slug"
            if util.IsUuidLike(search) {
                colName = "u.uuid"
                search = util.UuidFormatDb(search)
            } else if util.IsEmailLike(search) {
                colName = "u.email"
            } else {
                search = slug.Make(search)
            }
            qs = qs + fmt.Sprintf(
                "%s%s = ?",
                orStr,
                colName,
            )
            qargs = append(qargs, search)
        }
        qs = qs + ")"
    }
    // if qargs has nothing in it, a WHERE clause has not yet been added...
    if len(qargs) == 0 && opts.Marker != "" {
        qs = qs + "WHERE "
    }
    if opts.Marker != "" && len(opts.SortFields) > 0 {
        sqlutil.AddMarkerWhere(
            &qs,
            opts,
            "u",
            (len(qargs) > 0),
            &qargs,
            orgSortFields,
            s.orgSortFieldByUuid(opts.Marker, opts.SortFields[0]),
        )
    }

    sqlutil.AddOrderBy(&qs, opts, "u")
    qs = qs + "\nLIMIT ?"
    qargs = append(qargs, opts.Limit)

    rows, err := s.Rows(qs, qargs...)
    if err != nil {
        return nil, err
    }
    return rows, nil
}

// Returns a list of user IDs for users belonging to an entire organization
// tree excluding a supplied user ID
func (s *IAMStorage) usersInOrgTreeExcluding(
    rootOrgId uint64,
    excludeUserId uint64,
) ([]uint64, error) {
    m := s.Meta()
    outbl := m.TableDef("organization_users").As("ou")
    otbl := m.TableDef("organizations").As("o")
    colOUUserId := outbl.Column("user_id")
    colOUOrgId := outbl.Column("organization_id")
    colOrgId := otbl.Column("id")
    colRootOrgId := otbl.Column("root_organization_id")
    joinCond := sqlb.Equal(colOUOrgId, colOrgId)
    q := sqlb.Select(colOUUserId).Join(otbl, joinCond)
    q.Where(
        sqlb.And(
            sqlb.Equal(colRootOrgId, rootOrgId),
            sqlb.NotEqual(colOUUserId, excludeUserId),
        ),
    )
    qs, qargs := q.StringArgs()
    out := make([]uint64, 0)
    rows, err := s.Rows(qs, qargs...)
    if err != nil {
        return nil, err
    }
    defer rows.Close()
    for rows.Next() {
        var userId uint64
        err = rows.Scan(&userId)
        if err != nil {
            return nil, err
        }
        out = append(out, userId)
    }
    return out, nil
}

// Returns a list of user IDs for users belonging to one specific organization
// (not the entire tree) excluding a supplied user ID
func (s *IAMStorage) usersInOrgExcluding(
    orgId uint64,
    excludeUserId uint64,
) ([]uint64, error) {
    m := s.Meta()
    outbl := m.TableDef("organization_users").As("ou")
    colOUUserId := outbl.Column("user_id")
    colOUOrgId := outbl.Column("organization_id")
    q := sqlb.Select(colOUUserId)
    q.Where(
        sqlb.And(
            sqlb.Equal(colOUOrgId, orgId),
            sqlb.NotEqual(colOUUserId, excludeUserId),
        ),
    )
    qs, qargs := q.StringArgs()
    out := make([]uint64, 0)
    rows, err := s.Rows(qs, qargs...)
    if err != nil {
        return nil, err
    }
    defer rows.Close()
    for rows.Next() {
        var userId uint64
        err = rows.Scan(&userId)
        if err != nil {
            return nil, err
        }
        out = append(out, userId)
    }
    return out, nil
}

type orgToDelete struct {
    id uint64
    generation uint64
}

// Deletes a user, their membership in any organizations and all resources they
// have created. Also deletes root organizations that only the user is a member of.
func (s *IAMStorage) UserDelete(
    search string,
) error {
    defer s.log.WithSection("iam/storage")()

    userId := s.userIdFromIdentifier(search)
    if userId == 0 {
        return fmt.Errorf("No such user found.")
    }

    // Identify root organizations that the user is a member of. If those
    // organizations have child organizations that have users *other* than the
    // user we'd like to delete and there are no other users associated with
    // the *root* organization, return an error saying the user needs to
    // transfer ownership of the root organization by adding another user or
    // delete the organization entirely.
    qs := `
SELECT
  o.id
, o.uuid
, o.generation
FROM organization_users AS ou
JOIN organizations AS o
 ON ou.organization_id = o.id
WHERE ou.user_id = ?
AND o.parent_organization_id IS NULL
`
    rootOrgs, err := s.Rows(qs, userId)
    if err != nil {
        return err
    }
    defer rootOrgs.Close()

    orgsToDelete := make([]*orgToDelete, 0)
    for rootOrgs.Next() {
        var orgId uint64
        var orgUuid string
        var orgGeneration uint64
        err = rootOrgs.Scan(&orgId, &orgUuid, &orgGeneration)
        if err != nil {
            return err
        }
        otherUsers, err := s.usersInOrgTreeExcluding(orgId, userId)
        if err != nil {
            return err
        }
        if len(otherUsers) == 0 {
            // This is a root organization and there's no other users in the
            // entire organization tree, so mark it for deletion. There's no
            // point keeping it around.
            toDelete := &orgToDelete{
                id: orgId,
                generation: orgGeneration,
            }
            orgsToDelete = append(orgsToDelete, toDelete)
            continue
        } else {
            rootOtherUsers, err := s.usersInOrgExcluding(orgId, userId)
            if err != nil {
                return err
            }
            if len(rootOtherUsers) == 0 {
                // there are NOT other users associated to the root
                // organization but there ARE other users associated to child
                // organizations in the tree. Deleting the target user here
                // would leave this organization "orphaned" because there would
                // be no member of the root organization and thus no user could
                // delete the organization, add child organizations or add
                // members to the root organization. So, return an error to the
                // caller saying ownership must be transferred for this
                // organization or the organization needs to first be deleted.
                return errors.INVALID_WOULD_ORPHAN_ORGANIZATION(
                    search,
                    orgUuid,
                )
            }
        }
    }

    tx, err := s.Begin()
    if err != nil {
        return err
    }
    defer tx.Rollback()

    if len(orgsToDelete) > 0 {
        orgsInParam := sqlutil.InParamString(len(orgsToDelete))
        qargs := make([]interface{}, len(orgsToDelete))
        for x, orgId := range orgsToDelete {
            qargs[x] = orgId
        }
        qs = `
DELETE FROM organization_users
WHERE organization_id ` + orgsInParam + `
`
        s.log.SQL(qs)

        stmt, err := tx.Prepare(qs)
        if err != nil {
            return err
        }
        defer stmt.Close()
        _, err = stmt.Exec(qargs...)
        if err != nil {
            return err
        }

        qs = `
DELETE FROM organizations
WHERE id ` + orgsInParam + `
`
        s.log.SQL(qs)

        stmt, err = tx.Prepare(qs)
        if err != nil {
            return err
        }
        defer stmt.Close()
        _, err = stmt.Exec(qargs...)
        if err != nil {
            return err
        }
    }

    qs = `
DELETE FROM organization_users
WHERE user_id = ?
`
        s.log.SQL(qs)

    stmt, err := tx.Prepare(qs)
    if err != nil {
        return err
    }
    defer stmt.Close()
    _, err = stmt.Exec(userId)
    if err != nil {
        return err
    }

    qs = `
DELETE FROM users
WHERE id = ?
`
    s.log.SQL(qs)

    stmt, err = tx.Prepare(qs)
    if err != nil {
        return err
    }
    defer stmt.Close()
    _, err = stmt.Exec(userId)
    if err != nil {
        return err
    }

    err = tx.Commit()
    if err != nil {
        return err
    }
    return nil
}

// Given an identifier (email, slug, or UUID), return the user's internal
// integer ID. Returns 0 if the user could not be found.
func (s *IAMStorage) userIdFromIdentifier(
    identifier string,
) uint64 {
    var err error
    m := s.Meta()
    utbl := m.TableDef("users").As("u")
    colUserId := utbl.Column("id")
    q := sqlb.Select(colUserId)
    s.userWhere(q, identifier)
    qs, qargs := q.StringArgs()

    rows, err := s.Rows(qs, qargs...)
    if err != nil {
        return 0
    }
    defer rows.Close()
    output := uint64(0)
    for rows.Next() {
        err = rows.Scan(&output)
        if err != nil {
            return 0
        }
        break
    }
    return output
}

// Given an identifier (email, slug, or UUID), return the user's UUID. Returns
// empty string if the user could not be found.
func (s *IAMStorage) userUuidFromIdentifier(
    identifier string,
) string {
    var err error
    m := s.Meta()
    utbl := m.TableDef("users").As("u")
    colUserUuid := utbl.Column("uuid")
    q := sqlb.Select(colUserUuid)
    s.userWhere(q, identifier)
    qs, qargs := q.StringArgs()

    rows, err := s.Rows(qs, qargs...)
    if err != nil {
        return ""
    }
    defer rows.Close()
    output := ""
    for rows.Next() {
        err = rows.Scan(&output)
        if err != nil {
            return ""
        }
        break
    }
    return output
}

// Given a name, slug or UUID, returns that user or an error if the
// user could not be found
func (s *IAMStorage) userRecord(
    search string,
) (*userRecord, error) {
    qargs := make([]interface{}, 0)
    qs := `
SELECT
  id
, uuid
, email
, display_name
, slug
, generation
FROM users
WHERE `
    qs = buildUserGetWhere(qs, search, &qargs)

    rows, err := s.Rows(qs, qargs...)
    if err != nil {
        return nil, err
    }
    defer rows.Close()
    for rows.Next() {
        user:= &pb.User{}
        userRec := &userRecord{
            pb: user,
        }
        err = rows.Scan(
            &userRec.id,
            &user.Uuid,
            &user.Email,
            &user.DisplayName,
            &user.Slug,
            &user.Generation,
        )
        if err != nil {
            return nil, err
        }
        return userRec, nil
    }
    return nil, errors.NOTFOUND("user", search)
}

func (s *IAMStorage) userWhere(
    q *sqlb.SelectQuery,
    search string,
) {
    m := s.Meta()
    utbl := m.TableDef("users").As("u")
    colUserDisplayName := utbl.Column("display_name")
    colUserUuid := utbl.Column("uuid")
    colUserSlug := utbl.Column("slug")
    if util.IsUuidLike(search) {
        q.Where(sqlb.Equal(colUserUuid, util.UuidFormatDb(search)))
    } else {
        q.Where(
            sqlb.Or(
                sqlb.Equal(colUserDisplayName, search),
                sqlb.Equal(colUserSlug, search),
            ),
        )
    }
}

// Builds the WHERE clause for single user search by identifier
func buildUserGetWhere(
    qs string,
    search string,
    qargs *[]interface{},
) string {
    if util.IsUuidLike(search) {
        qs = qs + "uuid = ?"
        *qargs = append(*qargs, util.UuidFormatDb(search))
    } else if util.IsEmailLike(search) {
        qs = qs + "email = ?"
        *qargs = append(*qargs, strings.TrimSpace(search))
    } else {
        qs = qs + "display_name = ? OR slug = ?"
        *qargs = append(*qargs, search)
        *qargs = append(*qargs, search)
    }
    return qs
}

// Returns a pb.User record filled with information about a requested user.
func (s *IAMStorage) UserGet(
    search string,
) (*pb.User, error) {
    qargs := make([]interface{}, 0)
    qs := `
SELECT
  uuid
, email
, display_name
, slug
, generation
FROM users
WHERE `
    qs = buildUserGetWhere(qs, search, &qargs)

    rows, err := s.Rows(qs, qargs...)
    if err != nil {
        return nil, err
    }
    defer rows.Close()
    found := false
    user := &pb.User{}
    for rows.Next() {
        if found {
            return nil, errors.TOO_MANY_MATCHES(search)
        }
        err = rows.Scan(
            &user.Uuid,
            &user.Email,
            &user.DisplayName,
            &user.Slug,
            &user.Generation,
        )
        if err != nil {
            return nil, err
        }
        found = true
    }
    if ! found {
        return nil, errors.NOTFOUND("user", search)
    }
    return user, nil
}

// Creates a new record for a user
func (s *IAMStorage) UserCreate(
    fields *pb.UserSetFields,
) (*pb.User, error) {
    defer s.log.WithSection("iam/storage")()

    // Grab and check role IDs before starting transaction...
    var roleIds []int64
    var err error
    if fields.Roles != nil {
        roleIds, err = s.roleIdsFromIdentifiers(fields.Roles)
        if err != nil {
            return nil, err
        }
    }

    tx, err := s.Begin()
    if err != nil {
        return nil, err
    }
    defer tx.Rollback()

    qs := `
INSERT INTO users (uuid, email, display_name, slug, generation)
VALUES (?, ?, ?, ?, ?)
`
    s.log.SQL(qs)

    stmt, err := tx.Prepare(qs)
    if err != nil {
        return nil, err
    }
    uuid := util.Uuid4Char32()
    email := fields.Email.Value
    displayName := fields.DisplayName.Value
    slug := slug.Make(displayName)
    res, err := stmt.Exec(
        uuid,
        email,
        displayName,
        slug,
        1,
    )
    if err != nil {
        if sqlutil.IsDuplicateKey(err) {
            // Duplicate key, check if it's the slug or the email
            if sqlutil.IsDuplicateKeyOn(err, "uix_slug") {
                return nil, errors.DUPLICATE("display name", displayName)
            }
            if sqlutil.IsDuplicateKeyOn(err, "uix_email") {
                return nil, errors.DUPLICATE("email", email)
            }
        }
        return nil, err
    }
    user := &pb.User{
        Uuid: uuid,
        Email: email,
        DisplayName: displayName,
        Slug: slug,
        Generation: 1,
    }

    newUserId, err := res.LastInsertId()
    if err != nil {
        return nil, err
    }

    // Add any roles to the user
    if fields.Roles != nil {
        err = s.userAddRoles(tx, newUserId, roleIds)
        if err != nil {
            return nil, err
        }
    }

    err = tx.Commit()
    if err != nil {
        return nil, err
    }
    return user, nil
}

// Sets information for a user
func (s *IAMStorage) UserUpdate(
    before *pb.User,
    changed *pb.UserSetFields,
) (*pb.User, error) {
    defer s.log.WithSection("iam/storage")()

    uuid := before.Uuid
    qs := "UPDATE users SET "
    changes := make(map[string]interface{}, 0)
    newUser := &pb.User{
        Uuid: uuid,
        Generation: before.Generation + 1,
    }
    if changed.DisplayName != nil {
        newDisplayName := changed.DisplayName.Value
        newSlug := slug.Make(newDisplayName)
        changes["display_name"] = newDisplayName
        newUser.DisplayName = newDisplayName
        newUser.Slug = newSlug
    } else {
        newUser.DisplayName = before.DisplayName
        newUser.Slug = before.Slug
    }
    if changed.Email != nil {
        newEmail := changed.Email.Value
        changes["email"] = newEmail
        newUser.Email = newEmail
    } else {
        newUser.Email = before.Email
    }
    for field, _ := range changes {
        qs = qs + fmt.Sprintf("%s = ?, ", field)
    }
    // Trim off the last comma and space
    qs = qs[0:len(qs)-2]

    qs = qs + " WHERE uuid = ? AND generation = ?"

    s.log.SQL(qs)

    stmt, err := s.Prepare(qs)
    if err != nil {
        return nil, err
    }
    pargs := make([]interface{}, len(changes) + 2)
    x := 0
    for _, value := range changes {
        pargs[x] = value
        x++
    }
    pargs[x] = uuid
    x++
    pargs[x] = before.Generation
    _, err = stmt.Exec(pargs...)
    if err != nil {
        return nil, err
    }
    return newUser, nil
}

// Returns the organizations a user belongs to
func (s *IAMStorage) UserMembersList(
    req *pb.UserMembersListRequest,
) (storage.RowIterator, error) {
    defer s.log.WithSection("iam/storage")()

    // First verify the supplied user exists
    search := req.User
    userId := s.userIdFromIdentifier(search)
    if userId == 0 {
        notFound := fmt.Errorf("No such user found.")
        return nil, notFound
    }
    qs := `
SELECT
  o.uuid
, o.display_name
, o.slug
, o.generation
, po.display_name as parent_display_name
, po.slug as parent_slug
, po.uuid AS parent_organization_uuid
FROM organization_users AS ou
JOIN organizations AS o
 ON ou.organization_id = o.id
LEFT JOIN organizations AS po
 ON o.parent_organization_id = po.id
WHERE ou.user_id = ?
`
    rows, err := s.Rows(qs, userId)
    if err != nil {
        return nil, err
    }
    return rows, nil
}

// Returns the roles a user has
func (s *IAMStorage) UserRolesList(
    req *pb.UserRolesListRequest,
) (storage.RowIterator, error) {
    defer s.log.WithSection("iam/storage")()

    // First verify the supplied user exists
    search := req.User
    userId := s.userIdFromIdentifier(search)
    if userId == 0 {
        notFound := fmt.Errorf("No such user found.")
        return nil, notFound
    }
    qs := `
SELECT
  r.uuid
, r.display_name
, r.slug
, o.display_name as organization_display_name
, o.slug as organization_slug
, o.uuid as organization_uuid
FROM roles AS r
LEFT JOIN organizations AS o
 ON r.root_organization_id = o.id
JOIN user_roles AS ur
 ON r.id = ur.role_id
WHERE ur.user_id = ?
`
    rows, err := s.Rows(qs, userId)
    if err != nil {
        return nil, err
    }
    return rows, nil
}

// Returns the a user along with the user's permissions
func (s *IAMStorage) UserPermissionsGet(
    search string,
) (*pb.UserPermissions, error) {
    defer s.log.WithSection("iam/storage")()

    // First verify the supplied user exists
    userRec, err := s.userRecord(search)
    if err != nil {
        return nil, err
    }

    userId := userRec.id
    user := userRec.pb

    // Grab the system permissions (permissions for any unscoped role that the
    // user has)
    qs := `
SELECT
  rp.permission
FROM roles AS r
JOIN user_roles AS ur
 ON r.id = ur.role_id
JOIN role_permissions AS rp
 ON r.id = rp.role_id
WHERE r.root_organization_id IS NULL
AND ur.user_id = ?
GROUP BY rp.permission
`
    sysPerms := make([]pb.Permission, 0)
    rows, err := s.Rows(qs, userId)
    if err != nil {
        return nil, err
    }
    for rows.Next() {
        var perm int64
        err = rows.Scan(&perm)
        if err != nil {
            return nil, err
        }
        sysPerms = append(sysPerms, pb.Permission(perm))
    }

    // Now load the "scoped" permissions, which are the permissions that
    // correspond to roles that are scoped to a particular organization that
    // the user has
    qs = `
SELECT
  o.uuid, rp.permission
FROM roles AS r
JOIN user_roles AS ur
 ON r.id = ur.role_id
JOIN role_permissions AS rp
 ON r.id = rp.role_id
JOIN organizations AS o
 ON r.root_organization_id = o.id
AND ur.user_id = ?
GROUP BY o.uuid, rp.permission
ORDER BY o.uuid, rp.permission
`
    scopedPerms := make(map[string]*pb.PermissionSet, 0)
    rows, err = s.Rows(qs, userId)
    if err != nil {
        return nil, err
    }
    for rows.Next() {
        var perm int64
        var orgUuid string
        err = rows.Scan(&orgUuid, &perm)
        if err != nil {
            return nil, err
        }
        entry, ok := scopedPerms[orgUuid]
        if ! ok {
            entry = &pb.PermissionSet{
                Permissions: make([]pb.Permission, 0),
            }
            scopedPerms[orgUuid] = entry
        }
        entry.Permissions = append(entry.Permissions, pb.Permission(perm))
    }
    perms := &pb.UserPermissions{
        User: user,
        System: &pb.PermissionSet{
            Permissions: sysPerms,
        },
        Scoped: scopedPerms,
    }
    return perms, nil
}

// Given an internal integer identifier for a user and a set of role identifier
// strings, add the user to the roles.
func (s *IAMStorage) userAddRoles(
    tx *sql.Tx,
    userId int64,
    roleIds []int64,
) (error) {
    if len(roleIds) == 0 {
        return nil
    }
    defer s.log.WithSection("iam/storage")()

    s.log.L3("Adding roles %v to user %d", roleIds, userId)

    qs := `
INSERT INTO user_roles (
user_id
, role_id
) VALUES
`
    for x, _ := range roleIds {
        if x > 0 {
            qs = qs + "\n, (?, ?)"
        } else {
            qs = qs + "(?, ?)"
        }
    }

    s.log.SQL(qs)

    stmt, err := tx.Prepare(qs)
    if err != nil {
        return err
    }
    defer stmt.Close()

    // Add in the query parameters for each record
    qargs := make([]interface{}, 2 * (len(roleIds)))
    c := 0
    for _, roleId := range roleIds {
        qargs[c] = userId
        c++
        qargs[c] = roleId
        c++
    }
    _, err = stmt.Exec(qargs[0:c]...)
    if err != nil {
        return err
    }
    return nil
}

// INSERTs and DELETEs user to role mapping records. Returns the number of
// roles added and removed to/from the user.
func (s *IAMStorage) UserRolesSet(
    req *pb.UserRolesSetRequest,
) (uint64, uint64, error) {
    defer s.log.WithSection("iam/storage")()

    // First verify the supplied user exists
    search := req.User
    userId := s.userIdFromIdentifier(search)
    if userId == 0 {
        notFound := fmt.Errorf("No such user %s.", userId)
        return 0, 0, notFound
    }

    // Look up internal IDs for all supplied added and removed role
    // identifiers before starting transaction
    roleIdsAdd, err := s.roleIdsFromIdentifiers(req.Add)
    if err != nil {
        return 0, 0, err
    }
    roleIdsRemove, err := s.roleIdsFromIdentifiers(req.Remove)
    if err != nil {
        return 0, 0, err
    }

    for x, addId := range roleIdsAdd {
        for _, removeId := range roleIdsRemove {
            if addId == removeId {
                // Asked to add and remove the same role...
                err = fmt.Errorf(
                    "Cannot both add and remove role %s.",
                    req.Add[x],
                )
                return 0, 0, err
            }
        }
    }

    qargs := make([]interface{}, 2 * (len(roleIdsAdd) + len(roleIdsRemove)))
    c := 0
    for _, roleId := range roleIdsAdd {
        qargs[c] = userId
        c++
        qargs[c] = roleId
        c++
    }
    addedQargs := c
    if len(roleIdsRemove) > 0 {
        qargs[c] = userId
        c++
        for _, roleId := range roleIdsRemove {
            qargs[c] = roleId
            c++
        }
    }

    tx, err := s.Begin()
    if err != nil {
        return 0, 0, err
    }
    defer tx.Rollback()

    numAdded := int64(0)
    numRemoved := int64(0)
    if len(roleIdsAdd) > 0 {
        qs := `
INSERT INTO user_roles (
  user_id
, role_id
) VALUES
    `
        for x, _ := range roleIdsAdd {
            if x > 0 {
                qs = qs + "\n, (?, ?)"
            } else {
                qs = qs + "(?, ?)"
            }
        }

        s.log.SQL(qs)

        stmt, err := tx.Prepare(qs)
        if err != nil {
            return 0, 0, err
        }
        defer stmt.Close()
        res, err := stmt.Exec(qargs[0:addedQargs]...)
        if err != nil {
            return 0, 0, err
        }
        numAdded, err = res.RowsAffected()
        if err != nil {
            return 0, 0, err
        }
    }

    if len(roleIdsRemove) > 0 {
        qs := `
DELETE FROM user_roles
WHERE user_id = ?
AND role_id ` + sqlutil.InParamString(len(roleIdsRemove)) + `
`
        s.log.SQL(qs)

        stmt, err := tx.Prepare(qs)
        if err != nil {
            return 0, 0, err
        }
        defer stmt.Close()
        res, err := stmt.Exec(qargs[addedQargs:c]...)
        if err != nil {
            return 0, 0, err
        }
        numRemoved, err = res.RowsAffected()
        if err != nil {
            return 0, 0, err
        }
    }

    err = tx.Commit()
    if err != nil {
        return 0, 0, err
    }
    return uint64(numAdded), uint64(numRemoved), nil
}
