package server

import (
    "fmt"
    "database/sql"

    "golang.org/x/net/context"

    pb "github.com/jaypipes/procession/proto"

    "github.com/jaypipes/procession/pkg/iam/storage"
)

// RoleList looks up zero or more role records matching supplied filters and
// streams Role messages back to the caller
func (s *Server) RoleList(
    req *pb.RoleListRequest,
    stream pb.IAM_RoleListServer,
) error {
    reset := s.log.WithSection("iam/server")
    defer reset()
    roleRows, err := storage.RoleList(s.ctx, req.Filters)
    if err != nil {
        return err
    }
    defer roleRows.Close()
    for roleRows.Next() {
        role := pb.Role{}
        var org sql.NullString
        err := roleRows.Scan(
            &role.Uuid,
            &role.DisplayName,
            &role.Slug,
            &role.Generation,
            &org,
        )
        if org.Valid {
            role.Organization = &pb.StringValue{
                Value: org.String,
            }
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
    reset := s.log.WithSection("iam/server")
    defer reset()

    s.log.L3("Getting role %s", req.Search)

    role, err := storage.RoleGet(s.ctx, req.Search)
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
    reset := s.log.WithSection("iam/server")
    defer reset()
    search := req.Search
    err := storage.RoleDelete(s.ctx, search)
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
    reset := s.log.WithSection("iam/server")
    defer reset()
    changed := req.Changed

    if req.Search == nil {
        s.log.L3("Creating new role")

        newRole, err := storage.RoleCreate(
            req.Session,
            s.ctx,
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

    before, err := storage.RoleGet(s.ctx, req.Search.Value)
    if err != nil {
        return nil, err
    }
    if before.Uuid == "" {
        notFound := fmt.Errorf("No such role found.")
        return nil, notFound
    }

    newRole, err := storage.RoleUpdate(s.ctx, before, changed)
    if err != nil {
        return nil, err
    }
    resp := &pb.RoleSetResponse{
        Role: newRole,
    }
    s.log.L1("Updated role %s", newRole.Uuid)
    return resp, nil
}
