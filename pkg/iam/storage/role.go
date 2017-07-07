package storage

import (
    "database/sql"
    "fmt"
    "strings"

    "github.com/gosimple/slug"
    "github.com/go-sql-driver/mysql"

    "github.com/jaypipes/procession/pkg/util"
    "github.com/jaypipes/procession/pkg/sqlutil"
    "github.com/jaypipes/procession/pkg/storage"
    pb "github.com/jaypipes/procession/proto"
)

// Returns a storage.RowIterator yielding roles matching a set of supplied
// filters
func (s *Storage) RoleList(
    filters *pb.RoleListFilters,
) (storage.RowIterator, error) {
    numWhere := 0

    // TODO(jaypipes): Move this kind of stuff into a generic helper function
    // that can be re-used by user, org, role, etc
    if filters.Uuids != nil {
        numWhere = numWhere + len(filters.Uuids)
    }
    if filters.DisplayNames != nil {
        numWhere = numWhere + len(filters.DisplayNames)
    }
    if filters.Slugs != nil {
        numWhere = numWhere + len(filters.Slugs)
    }
    qargs := make([]interface{}, numWhere)
    qidx := 0
    qs := `
SELECT
  r.uuid
, r.display_name
, r.slug
, r.generation
, o.uuid AS organization_uuid
FROM roles AS r
LEFT JOIN organizations AS o
  ON r.root_organization_id = o.id
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

// Returns a pb.Role message filled with information about a requested role
func (s *Storage) RoleGet(
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
        var orgUuid sql.NullString
        err = rows.Scan(
            &roleId,
            &role.Uuid,
            &role.DisplayName,
            &role.Slug,
            &role.Generation,
            &orgUuid,
        )
        if err != nil {
            return nil, err
        }
        if orgUuid.Valid {
            sv := &pb.StringValue{Value: orgUuid.String}
            role.Organization = sv
        }
        break
    }

    perms, err := s.rolePermissionsById(roleId)
    if err != nil {
        return nil, err
    }
    role.PermissionSet = &pb.PermissionSet{
        Permissions: perms,
    }
    return &role, nil
}

// Deletes a role, their membership in any organizations and all resources they
// have created. Also deletes root organizations that only the role is a member of.
func (s *Storage) RoleDelete(
    search string,
) error {
    defer s.log.WithSection("iam/storage")()

    roleId := s.roleIdFromIdentifier(search)
    if roleId == 0 {
        return fmt.Errorf("No such role found.")
    }

    tx, err := s.db.Begin()
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
func (s *Storage) roleIdFromIdentifier(
    identifier string,
) uint64 {
    var err error
    qargs := make([]interface{}, 0)
    qs := "SELECT id FROM roles WHERE "
    qs = buildRoleGetWhere(qs, identifier, &qargs)

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

// TODO(jaypipes): Consolidate this and the org/user ones into a generic
// idFromUuid() helper function
// Returns the integer ID of a role given its UUID. Returns -1 if an role with
// the UUID was not found
func (s *Storage) roleIdFromUuid(
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
func (s *Storage) rolePermissionsById(
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
func (s *Storage) RoleCreate(
    sess *pb.Session,
    fields *pb.RoleSetFields,
) (*pb.Role, error) {
    defer s.log.WithSection("iam/storage")()

    tx, err := s.db.Begin()
    if err != nil {
        return nil, err
    }
    defer tx.Rollback()

    uuid := util.Uuid4Char32()
    displayName := fields.DisplayName.Value
    var rootOrgId int64
    var roleSlug string

    // Verify the supplied organization, if set, is even valid
    if fields.Organization != nil {
        org := fields.Organization.Value
        roleOrg, err := s.orgFromIdentifier(org)
        if err != nil {
            err := fmt.Errorf("No such organization found %s", org)
            return nil, err
        }
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
        perms := fields.Add.Permissions
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
        Organization: fields.Organization,
        PermissionSet: fields.Add,
        Generation: 1,
    }

    s.log.L2("Created new role %s (%s) with %d permissions",
           roleSlug, uuid, nPermsAdded)
    return role, nil
}

func (s *Storage) roleAddPermissions(
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

func (s *Storage) roleRemovePermissions(
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
func (s *Storage) RoleUpdate(
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

    tx, err := s.db.Begin()
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
        for _, p := range changed.Add.Permissions {
            addPerm := true
            for _, e := range existingPerms {
                if p == e {
                    addPerm = false
                    break
                }
                if changed.Remove != nil {
                    for _, r := range changed.Remove.Permissions {
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
        for _, p := range changed.Remove.Permissions {
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

    uuid := before.Uuid
    qs := `
UPDATE roles SET `
    changes := make(map[string]interface{}, 0)
    newRole := &pb.Role{
        Uuid: uuid,
        Generation: before.Generation + 1,
    }
    if changed.DisplayName != nil {
        newDisplayName := changed.DisplayName.Value
        newSlug := slug.Make(newDisplayName)
        changes["display_name"] = newDisplayName
        changes["slug"] = newSlug
        newRole.DisplayName = newDisplayName
        newRole.Slug = newSlug
    } else {
        newRole.DisplayName = before.DisplayName
        newRole.Slug = before.Slug
    }
    // Increment the generation
    changes["generation"] = before.Generation + 1
    for field, _ := range changes {
        qs = qs + fmt.Sprintf("%s = ?, ", field)
    }
    // Trim off the last comma and space
    qs = qs[0:len(qs)-2]

    qs = qs + "\nWHERE uuid = ? AND generation = ?"

    s.log.SQL(qs)

    stmt, err := tx.Prepare(qs)
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
    res, err := stmt.Exec(pargs...)
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
        return nil, ERR_CONCURRENT_UPDATE
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
    newRole.PermissionSet = &pb.PermissionSet{
        Permissions: newPerms,
    }

    s.log.L2("Updated role %s added %d, removed %d permissions",
             uuid, nPermsAdded, nPermsRemoved)
    return newRole, nil
}
