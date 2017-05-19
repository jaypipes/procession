package rpc

import (
    "fmt"

    "golang.org/x/net/context"

    pb "github.com/jaypipes/procession/proto"

    "github.com/jaypipes/procession/pkg/iam/db"
)

// UserGet looks up a user record by user identifier and returns the
// User protobuf message for the user
func (s *Server) UserGet(
    ctx context.Context,
    req *pb.UserGetRequest,
) (*pb.User, error) {
    user, err := db.UserGet(s.Db, req.Search)
    if err != nil {
        return nil, err
    }
    return user, nil
}

// UserList looks up zero or more user records matching supplied filters and
// streams User messages back to the caller
func (s *Server) UserList(
    req *pb.UserListRequest,
    stream pb.IAM_UserListServer,
) error {
    userRows, err := db.UserList(s.Db, req.Filters)
    if err != nil {
        return err
    }
    defer userRows.Close()
    user := pb.User{}
    for userRows.Next() {
        err := userRows.Scan(
            &user.Uuid,
            &user.Email,
            &user.DisplayName,
            &user.Slug,
            &user.Generation,
        )
        if err != nil {
            return err
        }
        if err = stream.Send(&user); err != nil {
            return err
        }
    }
    return nil
}

// UserSet creates a new user or updates an existing user
func (s *Server) UserSet(
    ctx context.Context,
    req *pb.UserSetRequest,
) (*pb.UserSetResponse, error) {
    changed := req.Changed
    if req.Search == nil {
        newUser, err := db.CreateUser(s.Db, changed)
        if err != nil {
            return nil, err
        }
        resp := &pb.UserSetResponse{
            User: newUser,
        }
        return resp, nil
    }
    before, err := db.UserGet(s.Db, req.Search.Value)
    if err != nil {
        return nil, err
    }
    if before.Uuid == "" {
        notFound := fmt.Errorf("No such user found.")
        return nil, notFound
    }

    newUser, err := db.UpdateUser(s.Db, before, changed)
    if err != nil {
        return nil, err
    }
    resp := &pb.UserSetResponse{
        User: newUser,
    }
    return resp, nil
}
