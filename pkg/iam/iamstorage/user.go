package iamstorage

import (
    "fmt"
    "strings"

    "github.com/gosimple/slug"

    "github.com/jaypipes/procession/pkg/util"
    "github.com/jaypipes/procession/pkg/sqlutil"
    "github.com/jaypipes/procession/pkg/storage"
    pb "github.com/jaypipes/procession/proto"
)

// Returns a sql.Rows yielding users matching a set of supplied filters
func (s *IAMStorage) UserList(
    filters *pb.UserListFilters,
) (storage.RowIterator, error) {
    numWhere := 0
    if filters.Uuids != nil {
        numWhere = numWhere + len(filters.Uuids)
    }
    if filters.DisplayNames != nil {
        numWhere = numWhere + len(filters.DisplayNames)
    }
    if filters.Emails != nil {
        numWhere = numWhere + len(filters.Emails)
    }
    if filters.Slugs != nil {
        numWhere = numWhere + len(filters.Slugs)
    }
    qargs := make([]interface{}, numWhere)
    qidx := 0
    qs := `
SELECT
  uuid
, email
, display_name
, slug
, generation
FROM users
`
    if numWhere > 0 {
        qs = qs + "WHERE "
        if filters.Uuids != nil {
            qs = qs + fmt.Sprintf(
                "uuid %s",
                sqlutil.InParamString(len(filters.Uuids)),
            )
            for _,  val := range filters.Uuids {
                qargs[qidx] = strings.TrimSpace(val)
                qidx++
            }
        }
        if filters.DisplayNames != nil {
            if qidx > 0{
                qs = qs + "\nAND "
            }
            qs = qs + fmt.Sprintf(
                "display_name %s",
                sqlutil.InParamString(len(filters.DisplayNames)),
            )
            for _,  val := range filters.DisplayNames {
                qargs[qidx] = strings.TrimSpace(val)
                qidx++
            }
        }
        if filters.Emails != nil {
            if qidx > 0 {
                qs = qs + "\nAND "
            }
            qs = qs + fmt.Sprintf(
                "email %s",
                sqlutil.InParamString(len(filters.Emails)),
            )
            for _,  val := range filters.Emails {
                qargs[qidx] = strings.TrimSpace(val)
                qidx++
            }
        }
        if filters.Slugs != nil {
            if qidx > 0 {
                qs = qs + "\nAND "
            }
            qs = qs + fmt.Sprintf(
                "slug %s",
                sqlutil.InParamString(len(filters.Slugs)),
            )
            for _,  val := range filters.Slugs {
                qargs[qidx] = strings.TrimSpace(val)
                qidx++
            }
        }
    }

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
    qs := `
SELECT ou.user_id
FROM organization_users AS ou
JOIN organizations AS o
 ON ou.organization_id = o.id
WHERE o.root_organization_id = ?
AND ou.user_id != ?
`
    out := make([]uint64, 0)
    rows, err := s.Rows(qs, rootOrgId, excludeUserId)
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
    qs := `
SELECT ou.user_id
FROM organization_users AS ou
WHERE ou.organization_id = ?
AND ou.user_id != ?
`
    out := make([]uint64, 0)
    rows, err := s.Rows(qs, orgId, excludeUserId)
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

func errCannotDeleteUserOrphanedOrg(
    user string,
    org string,
) error {
    return fmt.Errorf(`
Unable to delete user %s. This user is the sole member of organization %s which
has child organizations that would be orphaned by deleting the user. Please add
another user to organization %s's membership or manually delete the
organization.`, user, org, org)
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
                err = errCannotDeleteUserOrphanedOrg(search, orgUuid)
                return err
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
    qargs := make([]interface{}, 0)
    qs := "SELECT id FROM users WHERE "
    qs = buildUserGetWhere(qs, identifier, &qargs)

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
    qargs := make([]interface{}, 0)
    qs := `
SELECT uuid FROM users
WHERE `
    qs = buildUserGetWhere(qs, identifier, &qargs)

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
    user := pb.User{}
    for rows.Next() {
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
        break
    }
    return &user, nil
}

// Creates a new record for a user
func (s *IAMStorage) UserCreate(
    fields *pb.UserSetFields,
) (*pb.User, error) {
    defer s.log.WithSection("iam/storage")()

    qs := `
INSERT INTO users (uuid, email, display_name, slug, generation)
VALUES (?, ?, ?, ?, ?)
`
    s.log.SQL(qs)

    stmt, err := s.Prepare(qs)
    if err != nil {
        return nil, err
    }
    uuid := util.Uuid4Char32()
    email := fields.Email.Value
    displayName := fields.DisplayName.Value
    slug := slug.Make(displayName)
    _, err = stmt.Exec(
        uuid,
        email,
        displayName,
        slug,
        1,
    )
    if err != nil {
        return nil, err
    }
    user := &pb.User{
        Uuid: uuid,
        Email: email,
        DisplayName: displayName,
        Slug: slug,
        Generation: 1,
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

// Returns the union of all permissions for all system (non-scoped) roles for a
// user
func (s *IAMStorage) UserSystemPermissions(
    user string,
) ([]pb.Permission, error) {
    defer s.log.WithSection("iam/storage")()

    // First verify the supplied user exists
    userId := s.userIdFromIdentifier(user)
    if userId == 0 {
        return nil, storage.ERR_NOTFOUND_USER
    }
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
    perms := make([]pb.Permission, 0)
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
        perms = append(perms, pb.Permission(perm))
    }
    return perms, nil
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

    tx, err := s.Begin()
    if err != nil {
        return 0, 0, err
    }
    defer tx.Rollback()

    // Look up internal IDs for all supplied added and removed role
    // identifiers
    roleIdsAdd := make([]uint64, 0)
    for _, identifier := range req.Add {
        roleId := s.roleIdFromIdentifier(identifier)
        if roleId == 0 {
            notFound := fmt.Errorf("No such role %s.", identifier)
            return 0, 0, notFound
        }
        roleIdsAdd = append(roleIdsAdd, roleId)
    }
    roleIdsRemove := make([]uint64, 0)
    for _, identifier := range req.Remove {
        roleId := s.roleIdFromIdentifier(identifier)
        if roleId == 0 {
            notFound := fmt.Errorf("No such role %s.", identifier)
            return 0, 0, notFound
        }
        roleIdsRemove = append(roleIdsRemove, roleId)
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
