package rpc

import (
    "fmt"

    "golang.org/x/net/context"

    pb "github.com/jaypipes/procession/proto"

    "github.com/jaypipes/procession/pkg/action"

    "github.com/jaypipes/procession/pkg/iam/iamdb"
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
    uuid := request.UserUuid
    debug("> GetUser(%v)", uuid)

    user, _:= iamdb.GetUserByUuid(s.Db, uuid)
    debug("< %v", user)
    return user, nil
}

// SetUser creates a new user or updates an existing user
func (s *Server) SetUser(
    ctx context.Context,
    request *pb.SetUserRequest,
) (*pb.ActionReply, error) {
    user := request.User
    uuid := user.Uuid
    if uuid == "" {
        err := iamdb.CreateUser(s.Db, user)
        if err != nil {
            return action.Failure(err), err
        }
        out := action.Success(1)
        return out, nil
    }

    before, err := iamdb.GetUserByUuid(s.Db, uuid)
    if err != nil {
        return action.Failure(err), err
    }
    if before.Uuid == "" {
        notFound := fmt.Errorf("No such user found with UUID %s", uuid)
        return action.Failure(notFound), err
    }

    err = iamdb.UpdateUser(s.Db, before, user)
    if err != nil {
        return action.Failure(err), err
    }
    out := action.Success(1)
    return out, nil
}
