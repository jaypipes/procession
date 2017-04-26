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
    rows, err := db.Query("SELECT uuid, display_name, generation FROM users where uuid = ?", uuid)
    if err != nil {
        log.Fatal(err)
    }
    defer rows.Close()
    for rows.Next() {
        err := rows.Scan(&res.Uuid, &res.DisplayName, &res.Generation)
        if err != nil {
            log.Fatal(err)
        }
        log.Println(res)
    }
    err = rows.Err()
    if err != nil {
        log.Fatal(err)
    }
    return &res, nil
}
