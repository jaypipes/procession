package db

import (
    "fmt"
    "log"
    "database/sql"
    "strings"

    "github.com/gosimple/slug"

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

// Creates a new record for a organization
func CreateOrganization(db *sql.DB, fields *pb.SetOrganizationFields) (*pb.Organization, error) {
    qs := `
INSERT INTO organizations (uuid, display_name, slug, generation)
VALUES (?, ?, ?, ?)
`
    stmt, err := db.Prepare(qs)
    if err != nil {
        log.Fatal(err)
    }
    uuid := util.Uuid4Char32()
    displayName := fields.DisplayName.Value
    slug := slug.Make(displayName)
    _, err = stmt.Exec(
        uuid,
        displayName,
        slug,
        1,
    )
    if err != nil {
        return nil, err
    }
    organization := &pb.Organization{
        Uuid: uuid,
        DisplayName: displayName,
        Slug: slug,
        Generation: 1,
    }
    return organization, nil
}

// Sets information for a organization
func UpdateOrganization(
    db *sql.DB,
    before *pb.Organization,
    newFields *pb.SetOrganizationFields,
) (*pb.Organization, error) {
    uuid := before.Uuid
    qs := "UPDATE organizations SET "
    changes := make(map[string]interface{}, 0)
    newOrganization := &pb.Organization{
        Uuid: uuid,
        Generation: before.Generation + 1,
    }
    if newFields.DisplayName != nil {
        newDisplayName := newFields.DisplayName.Value
        newSlug := slug.Make(newDisplayName)
        changes["display_name"] = newDisplayName
        newOrganization.DisplayName = newDisplayName
        newOrganization.Slug = newSlug
    } else {
        newOrganization.DisplayName = before.DisplayName
        newOrganization.Slug = before.Slug
    }
    for field, _ := range changes {
        qs = qs + fmt.Sprintf("%s = ?, ", field)
    }
    // Trim off the last comma and space
    qs = qs[0:len(qs)-2]

    qs = qs + " WHERE uuid = ? AND generation = ?"

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
        return nil, err
    }
    return newOrganization, nil
}
