package rpc

import (
    "fmt"

    "golang.org/x/net/context"

    pb "github.com/jaypipes/procession/proto"

    "github.com/jaypipes/procession/pkg/iam/db"
)

func emptyUser() *pb.User {
    return &pb.User{}
}

// GetUser looks up a user record by user identifier and returns the
// User protobuf message for the user
func (s *Server) GetUser(
    ctx context.Context,
    request *pb.GetUserRequest,
) (*pb.User, error) {
    searchFields  := request.SearchFields
    debug("> GetUser(%v)", searchFields)

    user, err := db.GetUser(s.Db, searchFields)
    if err != nil {
        return nil, err
    }
    debug("< %v", user)
    return user, nil
}

// ListUsers looks up zero or more user records matching supplied filters and
// streams User messages back to the caller
func (s *Server) ListUsers(
    request *pb.ListUsersRequest,
    stream pb.IAM_ListUsersServer,
) error {
    filters := request.Filters
    debug("> ListUsers(%v)", filters)

    userRows, err := db.ListUsers(s.Db, filters)
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

// SetUser creates a new user or updates an existing user
func (s *Server) SetUser(
    ctx context.Context,
    request *pb.SetUserRequest,
) (*pb.SetUserResponse, error) {
    newFields := request.UserFields
    searchFields := request.SearchFields
    uuid := searchFields.Uuid.GetValue()
    if uuid == "" {
        newUser, err := db.CreateUser(s.Db, newFields)
        if err != nil {
            return nil, err
        }
        resp := &pb.SetUserResponse{
            User: newUser,
        }
        return resp, nil
    }
    before, err := db.GetUser(s.Db, searchFields)
    if err != nil {
        return nil, err
    }
    if before.Uuid == "" {
        notFound := fmt.Errorf("No such user found with UUID %s", uuid)
        return nil, notFound
    }

    newUser, err := db.UpdateUser(s.Db, before, newFields)
    if err != nil {
        return nil, err
    }
    resp := &pb.SetUserResponse{
        User: newUser,
    }
    return resp, nil
}
