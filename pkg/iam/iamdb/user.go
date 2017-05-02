package iamdb

import (
    "log"
    "database/sql"

    pb "github.com/jaypipes/procession/proto"
)

// Returns a pb.User record filled with information about a requested user.
func GetUserByUuid(db *sql.DB, uuid string) (*pb.User, error) {
    var err error
    res := pb.User{}
    rows, err := db.Query("SELECT uuid, display_name, email, generation FROM users where uuid = ?", uuid)
    if err != nil {
        log.Fatal(err)
    }
    err = rows.Err()
    if err != nil {
        log.Fatal(err)
    }
    defer rows.Close()
    for rows.Next() {
        err = rows.Scan(&res.Uuid, &res.DisplayName, &res.Email, &res.Generation)
        if err != nil {
            log.Fatal(err)
        }
        log.Println(res)
    }
    return &res, nil
}

// Sets information for a user
func UpdateUser(db *sql.DB, before *pb.User, after *pb.User) {
    qs := `
UPDATE users
SET display_name = ?
, email = ?
, generation = ?
WHERE uuid = ?
AND generation = ?
`
    rows, err := db.Query(
        qs,
        after.DisplayName,
        after.Email,
        before.Generation + 1,
        before.Uuid,
        before.Generation,
    )
    if err != nil {
        log.Fatal(err)
    }
    err = rows.Err()
    if err != nil {
        log.Fatal(err)
    }
    defer rows.Close()
}
