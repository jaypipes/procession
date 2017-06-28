package db

import (
    "database/sql"
    "log"

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
