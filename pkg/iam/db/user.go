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

const (
    trimChars = " \n\r\b\t"
)

func inParamString(numArgs int) string {
    qmarks := make([]string, numArgs)
    for x, _ := range(qmarks) {
        qmarks[x] = "?"
    }
    return strings.Join(qmarks, ",")
}

// Returns a sql.Rows yielding users matching a set of supplied filters
func ListUsers(db *sql.DB, filters *pb.ListUsersFilters) (*sql.Rows, error) {
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
    qs := "SELECT uuid, email, display_name, slug, generation FROM users"
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
        if filters.Emails != nil {
            if qidx > 0 {
                qs = qs + " AND "
            }
            qs = qs + fmt.Sprintf(
                "email IN (%s)",
                inParamString(len(filters.Emails)),
            )
            for _,  val := range filters.Emails {
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

// Returns a pb.User record filled with information about a requested user.
func GetUser(db *sql.DB, search string) (*pb.User, error) {
    var err error
    qargs := make([]interface{}, 0)
    qs := "SELECT uuid, email, display_name, slug, generation FROM users WHERE "
    if util.IsUuidLike(search) {
        qs = qs + "uuid = ?"
        qargs = append(qargs, util.UuidFormatDb(search))
    } else if util.IsEmailLike(search) {
        qs = qs + "email = ?"
        qargs = append(qargs, strings.TrimSpace(search))
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
    user := pb.User{}
    for rows.Next() {
        err = rows.Scan(&user.Uuid, &user.Email, &user.DisplayName, &user.Slug, &user.Generation)
        if err != nil {
            return nil, err
        }
        log.Println(user)
    }
    return &user, nil
}

// Creates a new record for a user
func CreateUser(db *sql.DB, fields *pb.SetUserFields) (*pb.User, error) {
    qs := `
INSERT INTO users (uuid, email, display_name, slug, generation)
VALUES (?, ?, ?, ?, ?)
`
    stmt, err := db.Prepare(qs)
    if err != nil {
        log.Fatal(err)
    }
    uuid := util.OrderedUuid()
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
func UpdateUser(
    db *sql.DB,
    before *pb.User,
    newFields *pb.SetUserFields,
) (*pb.User, error) {
    uuid := before.Uuid
    qs := "UPDATE users SET "
    changes := make(map[string]interface{}, 0)
    newUser := &pb.User{
        Uuid: uuid,
        Generation: before.Generation + 1,
    }
    if newFields.DisplayName != nil {
        newDisplayName := newFields.DisplayName.Value
        newSlug := slug.Make(newDisplayName)
        changes["display_name"] = newDisplayName
        newUser.DisplayName = newDisplayName
        newUser.Slug = newSlug
    } else {
        newUser.DisplayName = before.DisplayName
        newUser.Slug = before.Slug
    }
    if newFields.Email != nil {
        newEmail := newFields.Email.Value
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
    return newUser, nil
}
