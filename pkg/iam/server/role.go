package server

import (
    "fmt"
    "database/sql"

    "golang.org/x/net/context"

    pb "github.com/jaypipes/procession/proto"
)

// RoleList looks up zero or more role records matching supplied filters and
// streams Role messages back to the caller
func (s *Server) RoleList(
    req *pb.RoleListRequest,
    stream pb.IAM_RoleListServer,
) error {
    defer s.log.WithSection("iam/server")()

    roleRows, err := s.storage.RoleList(req)
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
            &role.Generation,
            &orgName,
            &orgSlug,
            &orgUuid,
        )
        if orgName.Valid {
            org := &pb.Organization{
                Uuid: orgUuid.String,
                DisplayName: orgName.String,
                Slug: orgSlug.String,
            }
            role.Organization = org
        }
        if err != nil {
            return err
        }
        if err = stream.Send(&role); err != nil {
            return err
        }
    }
    return nil
}

// RoleGet looks up a organization record by organization identifier
// and returns the Role protobuf message for the organization
func (s *Server) RoleGet(
    ctx context.Context,
    req *pb.RoleGetRequest,
) (*pb.Role, error) {
    defer s.log.WithSection("iam/server")()

    s.log.L3("Getting role %s", req.Search)

    role, err := s.storage.RoleGet(req.Search)
    if err != nil {
        return nil, err
    }
    return role, nil
}

// Deletes a role, all of its permission and user association records
func (s *Server) RoleDelete(
    ctx context.Context,
    req *pb.RoleDeleteRequest,
) (*pb.RoleDeleteResponse, error) {
    defer s.log.WithSection("iam/server")()

    search := req.Search
    err := s.storage.RoleDelete(search)
    if err != nil {
        return nil, err
    }
    s.log.L1("Deleted role %s", search)
    return &pb.RoleDeleteResponse{NumDeleted: 1}, nil
}

// RoleSet creates a new role or updates an existing
// role
func (s *Server) RoleSet(
    ctx context.Context,
    req *pb.RoleSetRequest,
) (*pb.RoleSetResponse, error) {
    defer s.log.WithSection("iam/server")()

    changed := req.Changed

    if req.Search == nil {
        s.log.L3("Creating new role")

        newRole, err := s.storage.RoleCreate(
            req.Session,
            changed,
        )
        if err != nil {
            return nil, err
        }
        resp := &pb.RoleSetResponse{
            Role: newRole,
        }
        s.log.L1("Created new role %s", newRole.Uuid)
        return resp, nil
    }

    s.log.L3("Updating role %s", req.Search.Value)

    before, err := s.storage.RoleGet(req.Search.Value)
    if err != nil {
        return nil, err
    }
    if before.Uuid == "" {
        notFound := fmt.Errorf("No such role found.")
        return nil, notFound
    }

    newRole, err := s.storage.RoleUpdate(before, changed)
    if err != nil {
        return nil, err
    }
    resp := &pb.RoleSetResponse{
        Role: newRole,
    }
    s.log.L1("Updated role %s", newRole.Uuid)
    return resp, nil
}
