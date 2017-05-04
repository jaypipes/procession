package iamdb

import (
    "log"
    "database/sql"

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
func CreateUser(db *sql.DB, user *pb.User) error {
    qs := `
INSERT INTO users VALUES (uuid, display_name, email, generation)
VALUES (?, ?, ?, ?)
`
    stmt, err := db.Prepare(qs)
    if err != nil {
        log.Fatal(err)
    }
    _, err = stmt.Exec(
        uuid.New(),
        user.DisplayName,
        user.Email,
        1,
    )
    if err != nil {
        log.Fatal(err)
    }
    return nil
}

// Sets information for a user
func UpdateUser(db *sql.DB, before *pb.User, after *pb.User) error {
    qs := `
UPDATE users
SET display_name = ?
, email = ?
, generation = ?
WHERE uuid = ?
AND generation = ?
`
    stmt, err := db.Prepare(qs)
    if err != nil {
        return err
    }
    _, err = stmt.Exec(
        after.DisplayName,
        after.Email,
        before.Generation + 1,
        before.Uuid,
        before.Generation,
    )
    if err != nil {
        return err
    }
    return nil
}
