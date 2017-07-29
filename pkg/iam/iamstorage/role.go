package iamstorage

import (
    "database/sql"
    "fmt"
    "strings"

    "github.com/gosimple/slug"
    "github.com/go-sql-driver/mysql"

    "github.com/jaypipes/procession/pkg/errors"
    "github.com/jaypipes/procession/pkg/sqlutil"
    "github.com/jaypipes/procession/pkg/storage"
    "github.com/jaypipes/procession/pkg/util"
    pb "github.com/jaypipes/procession/proto"
)

// Returns a storage.RowIterator yielding roles matching a set of supplied
// filters
func (s *IAMStorage) RoleList(
    filters *pb.RoleListFilters,
) (storage.RowIterator, error) {
    joinType := "LEFT"
    if filters.Organizations != nil {
        joinType = "INNER"
    }
    qs := fmt.Sprintf(`
SELECT
  r.uuid
, r.display_name
, r.slug
, r.generation
, o.display_name as organization_display_name
, o.slug as organization_slug
, o.uuid as organization_uuid
FROM roles AS r
%s JOIN organizations AS o
  ON r.root_organization_id = o.id
`, joinType)
    qargs := make([]interface{}, 0)
    if filters.Organizations != nil || filters.Identifiers != nil {
        qs = qs + "WHERE "
        if len(filters.Identifiers) > 1 {
            qs = qs + "("
        }
        for x, search := range filters.Identifiers {
            orStr := ""
            if x > 0 {
                orStr = "\nOR "
            }
            colName := "r.uuid"
            if ! util.IsUuidLike(search) {
                colName = "r.slug"
                search = slug.Make(search)
            }
            qs = qs + fmt.Sprintf(
                "%s%s = ?",
                orStr,
                colName,
            )
            qargs = append(qargs, search)
        }
        if len(filters.Identifiers) > 1 {
            qs = qs + ")"
        }
        if filters.Organizations != nil {
            if filters.Identifiers != nil {
                qs = qs + "\nAND "
            }
            orgIds := make([]int64, len(filters.Organizations))
            for x, org := range filters.Organizations {
                orgId := s.orgIdFromIdentifier(org)
                if orgId == 0 {
                    err := fmt.Errorf("No such organization %s", org)
                    return nil, err
                }
                orgIds[x] = orgId
            }
            qs = qs + fmt.Sprintf(
                "o.id %s",
                sqlutil.InParamString(len(orgIds)),
            )
            for _, orgId := range orgIds {
                qargs = append(qargs, orgId)
            }
        }
    }

    rows, err := s.Rows(qs, qargs...)
    if err != nil {
        return nil, err
    }
    return rows, nil
}

// Returns a pb.Role message filled with information about a requested role
func (s *IAMStorage) RoleGet(
    search string,
) (*pb.Role, error) {
    qargs := make([]interface{}, 0)
    qs := `
SELECT
  r.id
, r.uuid
, r.display_name
, r.slug
, r.generation
, o.display_name as organization_display_name
, o.slug as organization_slug
, o.uuid as organization_uuid
FROM roles AS r
LEFT JOIN organizations AS o
  ON r.root_organization_id = o.id
WHERE `
    if util.IsUuidLike(search) {
        qs = qs + "r.uuid = ?"
        qargs = append(qargs, util.UuidFormatDb(search))
    } else {
        qs = qs + "r.display_name = ? OR r.slug = ?"
        qargs = append(qargs, search)
        qargs = append(qargs, search)
    }

    rows, err := s.Rows(qs, qargs...)
    if err != nil {
        return nil, err
    }
    defer rows.Close()

    var roleId int64
    role := pb.Role{}
    for rows.Next() {
        var orgName sql.NullString
        var orgSlug sql.NullString
        var orgUuid sql.NullString
        err = rows.Scan(
            &roleId,
            &role.Uuid,
            &role.DisplayName,
            &role.Slug,
            &role.Generation,
            &orgName,
            &orgSlug,
            &orgUuid,
        )
        if err != nil {
            return nil, err
        }
        if orgUuid.Valid {
            org := &pb.Organization{
                Uuid: orgUuid.String,
                DisplayName: orgName.String,
                Slug: orgSlug.String,
            }
            role.Organization = org
        }
        break
    }

    perms, err := s.rolePermissionsById(roleId)
    if err != nil {
        return nil, err
    }
    role.Permissions = perms

    return &role, nil
}

// Deletes a role, their membership in any organizations and all resources they
// have created. Also deletes root organizations that only the role is a member of.
func (s *IAMStorage) RoleDelete(
    search string,
) error {
    defer s.log.WithSection("iam/storage")()

    roleId := s.roleIdFromIdentifier(search)
    if roleId == 0 {
        return fmt.Errorf("No such role found.")
    }

    tx, err := s.Begin()
    if err != nil {
        return err
    }
    defer tx.Rollback()

    qs := `
DELETE FROM user_roles
WHERE role_id = ?
`
    s.log.SQL(qs)

    stmt, err := tx.Prepare(qs)
    if err != nil {
        return err
    }
    defer stmt.Close()
    res, err := stmt.Exec(roleId)
    if err != nil {
        return err
    }
    nDelUsers, err := res.RowsAffected()
    if err != nil {
        return err
    }

    qs = `
DELETE FROM role_permissions
WHERE role_id = ?
`
    s.log.SQL(qs)

    stmt, err = tx.Prepare(qs)
    if err != nil {
        return err
    }
    defer stmt.Close()
    res, err = stmt.Exec(roleId)
    if err != nil {
        return err
    }
    nDelPerms, err := res.RowsAffected()
    if err != nil {
        return err
    }

    qs = `
DELETE FROM roles
WHERE id = ?
`
    s.log.SQL(qs)

    stmt, err = tx.Prepare(qs)
    if err != nil {
        return err
    }
    defer stmt.Close()
    _, err = stmt.Exec(roleId)
    if err != nil {
        return err
    }

    err = tx.Commit()
    if err != nil {
        return err
    }

    s.log.L2("Deleted role %d (%s) removed %d permissions and %d user " +
           "association records.", roleId, search, nDelUsers, nDelPerms)
    return nil
}

// TODO(jaypipes): Consolidate this and the org/user ones into a generic
// idFromIdentifier() helper function
// Given an identifier (email, slug, or UUID), return the role's internal
// integer ID. Returns 0 if the role could not be found.
func (s *IAMStorage) roleIdFromIdentifier(
    identifier string,
) int64 {
    var err error
    qargs := make([]interface{}, 0)
    qs := "SELECT id FROM roles WHERE "
    qs = buildRoleGetWhere(qs, identifier, &qargs)

    rows, err := s.Rows(qs, qargs...)
    if err != nil {
        return 0
    }
    defer rows.Close()
    var output int64
    for rows.Next() {
        err = rows.Scan(&output)
        if err != nil {
            return 0
        }
        break
    }
    return output
}

// TODO(jaypipes): Consolidate this and the org/user ones into a generic
// idFromUuid() helper function
// Returns the integer ID of a role given its UUID. Returns -1 if an role with
// the UUID was not found
func (s *IAMStorage) roleIdFromUuid(
    uuid string,
) int {
    qs := "SELECT id FROM roles WHERE uuid = ?"

    rows, err := s.Rows(qs, uuid)
    if err != nil {
        return -1
    }
    defer rows.Close()
    roleId := -1
    for rows.Next() {
        err = rows.Scan(&roleId)
        if err != nil {
            return -1
        }
    }
    return roleId
}

// TODO(jaypipes): Consolidate this and the org/user ones into a generic
// buildGenericWhere() helper function
// Builds the WHERE clause for single role search by identifier
func buildRoleGetWhere(
    qs string,
    search string,
    qargs *[]interface{},
) string {
    if util.IsUuidLike(search) {
        qs = qs + "uuid = ?"
        *qargs = append(*qargs, util.UuidFormatDb(search))
    } else {
        qs = qs + "display_name = ? OR slug = ?"
        *qargs = append(*qargs, search)
        *qargs = append(*qargs, search)
    }
    return qs
}

// Given a pb.Role message, populates the list of permissions for a specified role ID
func (s *IAMStorage) rolePermissionsById(
    roleId int64,
) ([]pb.Permission, error) {
    qs := `
SELECT
  rp.permission
FROM role_permissions AS rp
WHERE rp.role_id = ?
`
    rows, err := s.Rows(qs, roleId)
    if err != nil {
        return nil, err
    }
    defer rows.Close()

    perms := make([]pb.Permission, 0)
    for rows.Next() {
        var perm int64
        err = rows.Scan(
            &perm,
        )
        if err != nil {
            return nil, err
        }
        perms = append(perms, pb.Permission(perm))
    }
    return perms, nil
}

// Creates a new record for an role
func (s *IAMStorage) RoleCreate(
    sess *pb.Session,
    fields *pb.RoleSetFields,
) (*pb.Role, error) {
    defer s.log.WithSection("iam/storage")()

    tx, err := s.Begin()
    if err != nil {
        return nil, err
    }
    defer tx.Rollback()

    uuid := util.Uuid4Char32()
    displayName := fields.DisplayName.Value
    var rootOrgId int64
    var roleSlug string

    // Verify the supplied organization, if set, is valid
    var org *pb.Organization
    if fields.Organization != nil {
        orgIdentifier := fields.Organization.Value
        roleOrg, err := s.orgFromIdentifier(orgIdentifier)
        if err != nil {
            err := fmt.Errorf("No such organization found %s", orgIdentifier)
            return nil, err
        }
        org = roleOrg.pb
        rootOrgId = roleOrg.rootOrgId
        roleSlug = childOrgSlug(roleOrg.pb, displayName)
    } else {
        roleSlug = slug.Make(displayName)
    }

    qargs := make([]interface{}, 5)
    qargs[0] = uuid
    qargs[1] = displayName
    qargs[2] = roleSlug
    qargs[3] = 1  // generation

    if fields.Organization != nil {
        qargs[4] = rootOrgId
    } else {
        qargs[4] = nil
    }

    qs := `
INSERT INTO roles (
  uuid
, display_name
, slug
, generation
, root_organization_id
) VALUES (?, ?, ?, ?, ?)
`

    s.log.SQL(qs)

    stmt, err := tx.Prepare(qs)
    if err != nil {
        return nil, err
    }
    defer stmt.Close()
    res, err := stmt.Exec(qargs...)
    if err != nil {
        me, ok := err.(*mysql.MySQLError)
        if !ok {
            return nil, err
        }
        if me.Number == 1062 {
            // Duplicate key, check if it's the slug...
            if strings.Contains(me.Error(), "uix_slug") {
                return nil, fmt.Errorf("Duplicate display name.")
            }
        }
        return nil, err
    }
    newRoleId, err := res.LastInsertId()
    if err != nil {
        return nil, err
    }

    // Now add any permissions that were supplied
    var nPermsAdded int64
    if fields.Add != nil {
        perms := fields.Add
        nPermsAdded, err = s.roleAddPermissions(tx, newRoleId, perms)
        if err != nil {
            return nil, err
        }
    }

    err = tx.Commit()
    if err != nil {
        return nil, err
    }

    role := &pb.Role{
        Uuid: uuid,
        DisplayName: displayName,
        Slug: roleSlug,
        Organization: org,
        Permissions: fields.Add,
        Generation: 1,
    }

    s.log.L2("Created new role %s (%s) with %d permissions",
           roleSlug, uuid, nPermsAdded)
    return role, nil
}

// Returns the internal integer IDs of roles with supplied identifiers. If any
// role identifier isn't found, returns errors.NOTFOUND
func (s *IAMStorage) roleIdsFromIdentifiers(
    identifiers []string,
) ([]int64, error) {
    if len(identifiers) == 0 {
        return nil, nil
    }
    defer s.log.WithSection("iam/storage")()

    ids := make([]int64, len(identifiers))
    for x, identifier := range identifiers {
        roleId := s.roleIdFromIdentifier(identifier)
        if roleId == 0 {
            return nil, errors.NOTFOUND("role", identifier)
        }
        ids[x] = roleId
    }
    return ids, nil
}


func (s *IAMStorage) roleAddPermissions(
    tx *sql.Tx,
    roleId int64,
    perms []pb.Permission,
) (int64, error) {
    if len(perms) == 0 {
        return 0, nil
    }
    defer s.log.WithSection("iam/storage")()

    s.log.L2("Adding permissions %v to role %d", perms, roleId)

    qs := `
INSERT INTO role_permissions (
role_id
, permission
) VALUES
`
    for x, _ := range perms {
        if x > 0 {
            qs = qs + "\n, (?, ?)"
        } else {
            qs = qs + "(?, ?)"
        }
    }

    s.log.SQL(qs)

    stmt, err := tx.Prepare(qs)
    if err != nil {
        return 0, err
    }
    defer stmt.Close()

    // Add in the query parameters for each record
    qargs := make([]interface{}, 2 * (len(perms)))
    c := 0
    for _, perm := range perms {
        qargs[c] = roleId
        c++
        qargs[c] = perm
        c++
    }
    res, err := stmt.Exec(qargs[0:c]...)
    if err != nil {
        return 0, err
    }
    ra, err := res.RowsAffected()
    if err != nil {
        return 0, err
    }
    return ra, nil
}

func (s *IAMStorage) roleRemovePermissions(
    tx *sql.Tx,
    roleId int64,
    perms []pb.Permission,
) (int64, error) {
    if len(perms) == 0 {
        return 0, nil
    }
    defer s.log.WithSection("iam/storage")()

    s.log.L2("Removing permissions %v from role %d", perms, roleId)

    qs := `
DELETE FROM role_permissions
WHERE role_id = ?
AND permission ` + sqlutil.InParamString(len(perms)) + `
`

    s.log.SQL(qs)

    stmt, err := tx.Prepare(qs)
    if err != nil {
        return 0, err
    }
    defer stmt.Close()

    qargs := make([]interface{}, 1 + len(perms))
    c := 0
    qargs[c] = roleId
    c++
    for _, perm := range perms {
        qargs[c] = perm
        c++
    }
    res, err := stmt.Exec(qargs[0:c]...)
    if err != nil {
        return 0, err
    }
    ra, err := res.RowsAffected()
    if err != nil {
        return 0, err
    }
    return ra, nil
}

// Updates information for an existing role by examining the fields
// changed to the current fields values
func (s *IAMStorage) RoleUpdate(
    before *pb.Role,
    changed *pb.RoleSetFields,
) (*pb.Role, error) {
    defer s.log.WithSection("iam/storage")()

    roleId := int64(s.roleIdFromUuid(before.Uuid))
    if roleId == -1 {
        // Shouldn't happen unless another thread happened to delete the role
        // in between the start of our call and here, but let's be safe
        err := fmt.Errorf("No such role %s", before.Uuid)
        return nil, err
    }

    existingPerms, err := s.rolePermissionsById(roleId)
    if err != nil {
        return nil, err
    }

    tx, err := s.Begin()
    if err != nil {
        return nil, err
    }
    defer tx.Rollback()

    // The set of permissions for the new role that will be returned as part of
    // the Role message
    newPermsSet := make(map[pb.Permission]bool, 0)

    for _, e := range existingPerms {
        newPermsSet[e] = true
    }

    // Add any permissions that were supplied
    var nPermsAdded int64
    if changed.Add != nil {
        perms := make([]pb.Permission, 0)
        // Ignore any permissions that are either already in the existing
        // permissions or in the set of permissions requested to be removed.
        for _, p := range changed.Add {
            addPerm := true
            for _, e := range existingPerms {
                if p == e {
                    addPerm = false
                    break
                }
                if changed.Remove != nil {
                    for _, r := range changed.Remove {
                        if p == r {
                            addPerm = false
                            break
                        }
                    }
                }
            }
            if addPerm {
                perms = append(perms, p)
                newPermsSet[p] = true
            }
        }
        if len(perms) > 0 {
            nPermsAdded, err = s.roleAddPermissions(tx, roleId, perms)
            if err != nil {
                return nil, err
            }
        }
    }

    // Add any permissions that were supplied
    var nPermsRemoved int64
    if changed.Remove != nil {
        perms := make([]pb.Permission, 0)
        // Remove any permissions that are not in the existing permissions
        for _, p := range changed.Remove {
            for _, e := range existingPerms {
                if p == e {
                    perms = append(perms, p)
                    newPermsSet[p] = false
                }
            }
        }
        if len(perms) > 0 {
            nPermsRemoved, err = s.roleRemovePermissions(tx, roleId, perms)
            if err != nil {
                return nil, err
            }
        }
    }

    qs := `
UPDATE roles SET generation = ?`
    qargs := make([]interface{}, 0)
    newRole := &pb.Role{
        Uuid: before.Uuid,
        Generation: before.Generation + 1,
    }
    // Increment the generation
    qargs = append(qargs, before.Generation + 1)
    if changed.DisplayName != nil {
        newDisplayName := changed.DisplayName.Value
        newSlug := slug.Make(newDisplayName)
        qs = qs + ", display_name = ?, slug = ?"
        qargs = append(qargs, newDisplayName)
        qargs = append(qargs, newSlug)
        newRole.DisplayName = newDisplayName
        newRole.Slug = newSlug
    } else {
        newRole.DisplayName = before.DisplayName
        newRole.Slug = before.Slug
    }
    qs = qs + "\nWHERE id = ? AND generation = ?"

    qargs = append(qargs, roleId)
    qargs = append(qargs, before.Generation)

    s.log.SQL(qs)

    stmt, err := tx.Prepare(qs)
    if err != nil {
        return nil, err
    }
    res, err := stmt.Exec(qargs...)
    if err != nil {
        me, ok := err.(*mysql.MySQLError)
        if !ok {
            return nil, err
        }
        if me.Number == 1062 {
            // Duplicate key, check if it's the slug...
            if strings.Contains(me.Error(), "uix_slug_root_organization_id") {
                return nil, fmt.Errorf("Duplicate display name.")
            }
        }
        return nil, err
    }

    // Check for a concurrent update of the role by checking that a single row
    // was updated. If not, that means another thread updated the role in
    // between the time we started the transaction and here, so error out.
    ra, err := res.RowsAffected()
    if err != nil {
        return nil, err
    }
    if ra != 1 {
        return nil, storage.ERR_CONCURRENT_UPDATE
    }

    err = tx.Commit()
    if err != nil {
        return nil, err
    }

    newPerms := make([]pb.Permission, 0)
    for p, ok := range newPermsSet {
        if ok {
            newPerms = append(newPerms, p)
        }
    }
    newRole.Permissions = newPerms

    s.log.L2("Updated role %s added %d, removed %d permissions",
             before.Uuid, nPermsAdded, nPermsRemoved)
    return newRole, nil
}
