package rpc

import (
    "database/sql"
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
    reset := s.Ctx.LogSection("iam/rpc")
    defer reset()
    user, err := db.UserGet(s.Ctx, req.Search)
    if err != nil {
        return nil, err
    }
    return user, nil
}

// Deletes a user, all of its membership records and owned resources
func (s *Server) UserDelete(
    ctx context.Context,
    req *pb.UserDeleteRequest,
) (*pb.UserDeleteResponse, error) {
    reset := s.Ctx.LogSection("iam/rpc")
    defer reset()
    search := req.Search
    err := db.UserDelete(s.Ctx, search)
    if err != nil {
        return nil, err
    }
    s.Ctx.L1("Deleted user %s", search)
    return &pb.UserDeleteResponse{NumDeleted: 1}, nil
}

// UserList looks up zero or more user records matching supplied filters and
// streams User messages back to the caller
func (s *Server) UserList(
    req *pb.UserListRequest,
    stream pb.IAM_UserListServer,
) error {
    reset := s.Ctx.LogSection("iam/rpc")
    defer reset()
    userRows, err := db.UserList(s.Ctx, req.Filters)
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
    reset := s.Ctx.LogSection("iam/rpc")
    defer reset()
    changed := req.Changed
    if req.Search == nil {
        newUser, err := db.CreateUser(s.Ctx, changed)
        if err != nil {
            return nil, err
        }
        resp := &pb.UserSetResponse{
            User: newUser,
        }
        s.Ctx.L1("Created new user %s", newUser.Uuid)
        return resp, nil
    }
    before, err := db.UserGet(s.Ctx, req.Search.Value)
    if err != nil {
        return nil, err
    }
    if before.Uuid == "" {
        notFound := fmt.Errorf("No such user found.")
        return nil, notFound
    }

    newUser, err := db.UpdateUser(s.Ctx, before, changed)
    if err != nil {
        return nil, err
    }
    resp := &pb.UserSetResponse{
        User: newUser,
    }
    s.Ctx.L1("Updated user %s", newUser.Uuid)
    return resp, nil
}

// Return the organizations a user is a member of
func (s *Server) UserMembersList(
    req *pb.UserMembersListRequest,
    stream pb.IAM_UserMembersListServer,
) error {
    reset := s.Ctx.LogSection("iam/rpc")
    defer reset()
    orgRows, err := db.UserMembersList(s.Ctx, req)
    if err != nil {
        return err
    }
    defer orgRows.Close()
    for orgRows.Next() {
        org := pb.Organization{}
        var parentUuid sql.NullString
        err := orgRows.Scan(
            &org.Uuid,
            &org.DisplayName,
            &org.Slug,
            &org.Generation,
            &parentUuid,
        )
        if err != nil {
            return err
        }
        if parentUuid.Valid {
            sv := pb.StringValue{Value: parentUuid.String}
            org.ParentUuid = &sv
        }
        if err = stream.Send(&org); err != nil {
            return err
        }
    }
    return nil
}
