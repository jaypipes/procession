package rpc

import (
    "fmt"

    "golang.org/x/net/context"

    pb "github.com/jaypipes/procession/proto"

    "github.com/jaypipes/procession/pkg/action"

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
    getUser  := request.User
    debug("> GetUser(%v)", getUser)

    gotUser, _:= db.GetUser(s.Db, getUser)
    debug("< %v", gotUser)
    return gotUser, nil
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
        if err := userRows.Scan(&user); err != nil {
            return err
        }
        if err := stream.Send(&user); err != nil {
            return err
        }
    }
    return nil
}

// SetUser creates a new user or updates an existing user
func (s *Server) SetUser(
    ctx context.Context,
    request *pb.SetUserRequest,
) (*pb.ActionReply, error) {
    user := request.User
    uuid := user.Uuid
    if uuid == "" {
        err := db.CreateUser(s.Db, user)
        if err != nil {
            return action.Failure(err), err
        }
        out := action.Success(1)
        return out, nil
    }

    getUser := &pb.GetUser{
        Uuid: &pb.StringValue{
            Value:uuid,
        },
    }
    before, err := db.GetUser(s.Db, getUser)
    if err != nil {
        return action.Failure(err), err
    }
    if before.Uuid == "" {
        notFound := fmt.Errorf("No such user found with UUID %s", uuid)
        return action.Failure(notFound), err
    }

    err = db.UpdateUser(s.Db, before, user)
    if err != nil {
        return action.Failure(err), err
    }
    out := action.Success(1)
    return out, nil
}
