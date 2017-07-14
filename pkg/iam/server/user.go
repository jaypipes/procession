package server

import (
    "database/sql"
    "fmt"

    "golang.org/x/net/context"

    pb "github.com/jaypipes/procession/proto"
)

// UserGet looks up a user record by user identifier and returns the
// User protobuf message for the user
func (s *Server) UserGet(
    ctx context.Context,
    req *pb.UserGetRequest,
) (*pb.User, error) {
    defer s.log.WithSection("iam/server")()

    user, err := s.storage.UserGet(req.Search)
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
    defer s.log.WithSection("iam/server")()

    search := req.Search
    err := s.storage.UserDelete(search)
    if err != nil {
        return nil, err
    }
    s.log.L1("Deleted user %s", search)
    return &pb.UserDeleteResponse{NumDeleted: 1}, nil
}

// UserList looks up zero or more user records matching supplied filters and
// streams User messages back to the caller
func (s *Server) UserList(
    req *pb.UserListRequest,
    stream pb.IAM_UserListServer,
) error {
    defer s.log.WithSection("iam/server")()

    userRows, err := s.storage.UserList(req.Filters)
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
    defer s.log.WithSection("iam/server")()

    changed := req.Changed
    if req.Search == nil {
        newUser, err := s.storage.UserCreate(changed)
        if err != nil {
            return nil, err
        }
        resp := &pb.UserSetResponse{
            User: newUser,
        }
        s.log.L1("Created new user %s", newUser.Uuid)
        return resp, nil
    }
    before, err := s.storage.UserGet(req.Search.Value)
    if err != nil {
        return nil, err
    }
    if before.Uuid == "" {
        notFound := fmt.Errorf("No such user found.")
        return nil, notFound
    }

    newUser, err := s.storage.UserUpdate(before, changed)
    if err != nil {
        return nil, err
    }
    resp := &pb.UserSetResponse{
        User: newUser,
    }
    s.log.L1("Updated user %s", newUser.Uuid)
    return resp, nil
}

// Return the organizations a user is a member of
func (s *Server) UserMembersList(
    req *pb.UserMembersListRequest,
    stream pb.IAM_UserMembersListServer,
) error {
    defer s.log.WithSection("iam/server")()

    orgRows, err := s.storage.UserMembersList(req)
    if err != nil {
        return err
    }
    defer orgRows.Close()
    for orgRows.Next() {
        org := pb.Organization{}
        var parentName sql.NullString
        var parentSlug sql.NullString
        var parentUuid sql.NullString
        err := orgRows.Scan(
            &org.Uuid,
            &org.DisplayName,
            &org.Slug,
            &org.Generation,
            &parentName,
            &parentSlug,
            &parentUuid,
        )
        if err != nil {
            return err
        }
        if parentName.Valid {
            parent := &pb.Organization{
                DisplayName: parentName.String,
                Slug: parentSlug.String,
                Uuid: parentUuid.String,
            }
            org.Parent = parent
        }
        if err = stream.Send(&org); err != nil {
            return err
        }
    }
    return nil
}

// Return the roles a user has
func (s *Server) UserRolesList(
    req *pb.UserRolesListRequest,
    stream pb.IAM_UserRolesListServer,
) error {
    defer s.log.WithSection("iam/server")()

    roleRows, err := s.storage.UserRolesList(req)
    if err != nil {
        return err
    }
    defer roleRows.Close()
    for roleRows.Next() {
        role := pb.Role{}
        var orgName sql.NullString
        var orgSlug sql.NullString
        var orgUuid sql.NullString
        err := roleRows.Scan(
            &role.Uuid,
            &role.DisplayName,
            &role.Slug,
            &orgName,
            &orgSlug,
            &orgUuid,
        )
        if err != nil {
            return err
        }
        if orgName.Valid {
            org := &pb.Organization{
                Uuid: orgUuid.String,
                DisplayName: orgName.String,
                Slug: orgSlug.String,
            }
            role.Organization = org
        }
        if err = stream.Send(&role); err != nil {
            return err
        }
    }
    return nil
}

// Add or remove roles from a user
func (s *Server) UserRolesSet(
    ctx context.Context,
    req *pb.UserRolesSetRequest,
) (*pb.UserRolesSetResponse, error) {
    defer s.log.WithSection("iam/server")()

    added, removed, err := s.storage.UserRolesSet(req)
    if err != nil {
        return nil, err
    }
    resp := &pb.UserRolesSetResponse{
        NumAdded: added,
        NumRemoved: removed,
    }
    s.log.L1(
        "Updated roles for user  %s (added %d, removed %d)",
         req.User,
         added,
         removed,
    )
    return resp, nil
}
