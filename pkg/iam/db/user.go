package db

import (
    "fmt"
    "log"
    "database/sql"
    "strings"

    "github.com/pborman/uuid"

    pb "github.com/jaypipes/procession/proto"
)

// Returns a sql.Rows yielding users matching a set of supplied filters
func ListUsers(db *sql.DB, filters *pb.ListUsersFilters) (*sql.Rows, error) {
    numWhere := 0
    if filters.Uuids != nil { numWhere++ }
    if filters.DisplayNames != nil {numWhere++ }
    if filters.Emails != nil { numWhere ++ }
    qargs := make([]interface{}, numWhere)
    qidx := 0
    qs := "SELECT uuid, display_name, email, generation FROM users WHERE "
    if filters.Uuids != nil {
        qs = qs + "uuid IN (?)"
        qargs[qidx] = filters.Uuids
        qidx++
    }
    if filters.DisplayNames != nil {
        if qidx > 0{
            qs = qs + " AND "
        }
        qs = qs + "display_name IN (?)"
        qargs[qidx] = filters.DisplayNames
        qidx++
    }
    if filters.Emails != nil {
        if qidx > 0 {
            qs = qs + " AND "
        }
        qs = qs + "email IN (?)"
        qargs[qidx] = filters.Emails
        qidx++
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
func GetUser(db *sql.DB, getUser *pb.GetUser) (*pb.User, error) {
    var err error
    numWhere := 0
    if getUser.Uuid != nil { numWhere++ }
    if getUser.DisplayName != nil {numWhere++ }
    if getUser.Email != nil { numWhere ++ }
    if numWhere == 0 {
        err = fmt.Errorf("Must supply a UUID, display name or email to " +
                         "search for a user.")
        return nil, err
    }
    qargs := make([]interface{}, numWhere)
    qidx := 0
    res := pb.User{}
    qs := "SELECT uuid, display_name, email, generation FROM users WHERE "
    if getUser.Uuid != nil {
        qs = qs + "uuid = ?"
        qargs[qidx] = getUser.Uuid.Value
        qidx++
    }
    if getUser.DisplayName != nil {
        if qidx > 0{
            qs = qs + " AND "
        }
        qs = qs + "display_name = ?"
        qargs[qidx] = getUser.DisplayName.Value
        qidx++
    }
    if getUser.Email != nil {
        if qidx > 0 {
            qs = qs + " AND "
        }
        qs = qs + "email = ?"
        qargs[qidx] = getUser.Email.Value
        qidx++
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
    for rows.Next() {
        err = rows.Scan(&res.Uuid, &res.DisplayName, &res.Email, &res.Generation)
        if err != nil {
            return nil, err
        }
        log.Println(res)
    }
    return &res, nil
}

// Creates a new record for a user
func CreateUser(db *sql.DB, user *pb.SetUser) error {
    qs := `
INSERT INTO users (uuid, display_name, email, generation)
VALUES (?, ?, ?, ?)
`
    stmt, err := db.Prepare(qs)
    if err != nil {
        log.Fatal(err)
    }
    _, err = stmt.Exec(
        strings.Replace(uuid.New(), "-", "", 4),
        user.DisplayName.GetValue(),
        user.Email.GetValue(),
        1,
    )
    if err != nil {
        return err
    }
    return nil
}

// Sets information for a user
func UpdateUser(
    db *sql.DB,
    before *pb.User,
    user *pb.SetUser,
)  error {
    qs := "UPDATE users SET "
    changes := make(map[string]interface{}, 0)
    if user.DisplayName != nil {
        changes["display_name"] = user.DisplayName.Value
    }
    if user.Email != nil {
        changes["email"] = user.Email.Value
    }
    for field, _ := range changes {
        qs = qs + fmt.Sprintf("%s = ?, ", field)
    }
    // Trim off the last comma and space
    qs = qs[0:len(qs)-2]

    qs = qs + " WHERE uuid = ? AND generation = ?"

    stmt, err := db.Prepare(qs)
    if err != nil {
        return err
    }
    pargs := make([]interface{}, len(changes) + 2)
    x := 0
    for _, value := range changes {
        pargs[x] = value
        x++
    }
    pargs[x] = user.Uuid
    x++
    pargs[x] = before.Generation
    _, err = stmt.Exec(pargs...)
    if err != nil {
        return err
    }
    return nil
}
