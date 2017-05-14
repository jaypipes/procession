package db

import (
    "log"
    "database/sql"

    pb "github.com/jaypipes/procession/proto"
    "github.com/jaypipes/procession/pkg/util"
)

// Returns a pb.Organization record filled with information about a requested organization.
func GetOrganization(db *sql.DB, search string) (*pb.Organization, error) {
    var err error
    qargs := make([]interface{}, 0)
    qs := "SELECT uuid, display_name, slug, generation FROM organizations WHERE "
    if util.IsUuidLike(search) {
        qs = qs + "uuid = ?"
        qargs = append(qargs, util.UuidFormatDb(search))
    } else {
        qs = qs + "display_name = ? OR slug = ?"
        qargs = append(qargs, search)
        qargs = append(qargs, search)
    }

    rows, err := db.Query(qs, qargs...)
    if err != nil {
        return nil, err
    }
    err = rows.Err()
    if err != nil {
        return nil, err
    }
    defer rows.Close()
    organization := pb.Organization{}
    for rows.Next() {
        err = rows.Scan(&organization.Uuid, &organization.DisplayName, &organization.Slug, &organization.Generation)
        if err != nil {
            return nil, err
        }
        log.Println(organization)
    }
    return &organization, nil
}
