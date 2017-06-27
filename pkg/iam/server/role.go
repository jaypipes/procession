package server

import (
    "golang.org/x/net/context"

    pb "github.com/jaypipes/procession/proto"

    "github.com/jaypipes/procession/pkg/iam/db"
)

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
