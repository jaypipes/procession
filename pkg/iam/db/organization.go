package db

import (
    "fmt"
    "log"
    "database/sql"
    "strings"

    pb "github.com/jaypipes/procession/proto"
    "github.com/jaypipes/procession/pkg/util"
)

// Returns a sql.Rows yielding organizations matching a set of supplied filters
func ListOrganizations(db *sql.DB, filters *pb.ListOrganizationsFilters) (*sql.Rows, error) {
    numWhere := 0
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
    qs := "SELECT uuid, display_name, slug, generation FROM organizations"
    if numWhere > 0 {
        qs = qs + " WHERE "
        if filters.Uuids != nil {
            qs = qs + fmt.Sprintf(
                "uuid IN (%s)",
                inParamString(len(filters.Uuids)),
            )
            for _,  val := range filters.Uuids {
                qargs[qidx] = strings.Trim(val, trimChars)
                qidx++
            }
        }
        if filters.DisplayNames != nil {
            if qidx > 0{
                qs = qs + " AND "
            }
            qs = qs + fmt.Sprintf(
                "display_name IN (%s)",
                inParamString(len(filters.DisplayNames)),
            )
            for _,  val := range filters.DisplayNames {
                qargs[qidx] = strings.Trim(val, trimChars)
                qidx++
            }
        }
        if filters.Slugs != nil {
            if qidx > 0 {
                qs = qs + " AND "
            }
            qs = qs + fmt.Sprintf(
                "slug IN (%s)",
                inParamString(len(filters.Slugs)),
            )
            for _,  val := range filters.Slugs {
                qargs[qidx] = strings.Trim(val, trimChars)
                qidx++
            }
        }
    }

    rows, err := db.Query(qs, qargs...)
    if err != nil {
        return nil, err
    }
    err = rows.Err()
    if err != nil {
        return nil, err
    }
    return rows, nil
}

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
