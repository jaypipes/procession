package db

import (
    "database/sql"
    "fmt"
    "log"
    "strings"

    "github.com/gosimple/slug"
    "github.com/go-sql-driver/mysql"

    "github.com/jaypipes/procession/pkg/context"
    "github.com/jaypipes/procession/pkg/util"
    pb "github.com/jaypipes/procession/proto"
)

// Returns a pb.Role message filled with information about a requested role
func RoleGet(
    ctx *context.Context,
    search string,
) (*pb.Role, error) {
    reset := ctx.LogSection("iam/db")
    defer reset()
    db := ctx.Db
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

    ctx.LSQL(qs)

    rows, err := db.Query(qs, qargs...)
    if err != nil {
        return nil, err
    }
    err = rows.Err()
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
            role.OrganizationUuid = sv
        }
        break
    }

    perms, err := RolePermissionsGetById(ctx, roleId)
    if err != nil {
        return nil, err
    }
    role.PermissionSet = &pb.PermissionSet{
        Permissions: perms,
    }
    return &role, nil
}

// Given a pb.Role message, populates the list of permissions for a specified role ID
func RolePermissionsGetById(
    ctx *context.Context,
    roleId int64,
) ([]pb.Permission, error) {
    reset := ctx.LogSection("iam/db")
    defer reset()
    db := ctx.Db
    qs := `
SELECT
  rp.permission
FROM role_permissions AS rp
WHERE rp.role_id = ?
`
    ctx.LSQL(qs)

    rows, err := db.Query(qs, roleId)
    if err != nil {
        log.Fatal(err)
    }
    err = rows.Err()
    if err != nil {
        return nil, err
    }

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
func RoleCreate(
    sess *pb.Session,
    ctx *context.Context,
    fields *pb.RoleSetFields,
) (*pb.Role, error) {
    reset := ctx.LogSection("iam/db")
    defer reset()
    db := ctx.Db
    tx, err := db.Begin()
    if err != nil {
        log.Fatal(err)
    }
    defer tx.Rollback()

    uuid := util.Uuid4Char32()
    displayName := fields.DisplayName.Value
    slug := slug.Make(displayName)
    var rootOrgId interface{}
    if fields.OrganizationUuid != nil {
        rootOrgUuid := fields.OrganizationUuid.Value
        rootOrgInternalId := orgIdFromIdentifier(ctx, rootOrgUuid)
        if rootOrgInternalId == 0 {
            err = fmt.Errorf("No such organization %s", rootOrgUuid)
            return nil, err
        }
        rootOrgId = rootOrgInternalId
    }

    qs := `
INSERT INTO roles (
  uuid
, display_name
, slug
, root_organization_id
, generation
) VALUES (?, ?, ?, ?, ?)
`

    ctx.LSQL(qs)

    stmt, err := tx.Prepare(qs)
    if err != nil {
        log.Fatal(err)
    }
    defer stmt.Close()
    _, err = stmt.Exec(
        uuid,
        displayName,
        slug,
        rootOrgId,
        1,
    )
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

    err = tx.Commit()
    if err != nil {
        return nil, err
    }

    role := &pb.Role{
        Uuid: uuid,
        DisplayName: displayName,
        Slug: slug,
        OrganizationUuid: fields.OrganizationUuid,
        Generation: 1,
    }

    ctx.L2("Created new root role %s (%s)", slug, uuid)
    return role, nil
}

// Updates information for an existing role by examining the fields
// changed to the current fields values
func RoleUpdate(
    ctx *context.Context,
    before *pb.Role,
    changed *pb.RoleSetFields,
) (*pb.Role, error) {
    reset := ctx.LogSection("iam/db")
    defer reset()
    db := ctx.Db
    uuid := before.Uuid
    qs := "UPDATE roles SET "
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

    ctx.LSQL(qs)

    stmt, err := db.Prepare(qs)
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
    return newRole, nil
}
