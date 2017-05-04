package iamdb

import (
    "fmt"
    "log"
    "database/sql"
    "strings"

    "github.com/pborman/uuid"

    pb "github.com/jaypipes/procession/proto"
)

// Returns a pb.User record filled with information about a requested user.
func GetUserByUuid(db *sql.DB, uuid string) (*pb.User, error) {
    var err error
    res := pb.User{}
    rows, err := db.Query("SELECT uuid, display_name, email, generation FROM users where uuid = ?", uuid)
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
func CreateUser(db *sql.DB, user *pb.SetUserRequest_SetUser) error {
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
    user *pb.SetUserRequest_SetUser,
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
