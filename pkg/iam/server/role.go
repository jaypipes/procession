package server

import (
    "fmt"

    "golang.org/x/net/context"

    pb "github.com/jaypipes/procession/proto"

    "github.com/jaypipes/procession/pkg/iam/db"
)

// RoleList looks up zero or more role records matching supplied filters and
// streams Role messages back to the caller
func (s *Server) RoleList(
    req *pb.RoleListRequest,
    stream pb.IAM_RoleListServer,
) error {
    reset := s.Ctx.LogSection("iam/server")
    defer reset()
    roleRows, err := db.RoleList(s.Ctx, req.Filters)
    if err != nil {
        return err
    }
    defer roleRows.Close()
    role := pb.Role{}
    for roleRows.Next() {
        err := roleRows.Scan(
            &role.Uuid,
            &role.DisplayName,
            &role.Slug,
            &role.Generation,
        )
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
    reset := s.Ctx.LogSection("iam/server")
    defer reset()

    s.Ctx.L3("Getting role %s", req.Search)

    role, err := db.RoleGet(s.Ctx, req.Search)
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
    reset := s.Ctx.LogSection("iam/server")
    defer reset()
    search := req.Search
    err := db.RoleDelete(s.Ctx, search)
    if err != nil {
        return nil, err
    }
    s.Ctx.L1("Deleted role %s", search)
    return &pb.RoleDeleteResponse{NumDeleted: 1}, nil
}

// RoleSet creates a new role or updates an existing
// role
func (s *Server) RoleSet(
    ctx context.Context,
    req *pb.RoleSetRequest,
) (*pb.RoleSetResponse, error) {
    reset := s.Ctx.LogSection("iam/server")
    defer reset()
    changed := req.Changed

    if req.Search == nil {
        s.Ctx.L3("Creating new role")

        newRole, err := db.RoleCreate(
            req.Session,
            s.Ctx,
            changed,
        )
        if err != nil {
            return nil, err
        }
        resp := &pb.RoleSetResponse{
            Role: newRole,
        }
        s.Ctx.L1("Created new role %s", newRole.Uuid)
        return resp, nil
    }

    s.Ctx.L3("Updating role %s", req.Search.Value)

    before, err := db.RoleGet(s.Ctx, req.Search.Value)
    if err != nil {
        return nil, err
    }
    if before.Uuid == "" {
        notFound := fmt.Errorf("No such role found.")
        return nil, notFound
    }

    newRole, err := db.RoleUpdate(s.Ctx, before, changed)
    if err != nil {
        return nil, err
    }
    resp := &pb.RoleSetResponse{
        Role: newRole,
    }
    s.Ctx.L1("Updated role %s", newRole.Uuid)
    return resp, nil
}
