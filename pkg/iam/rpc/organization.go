package rpc

import (
    "golang.org/x/net/context"

    pb "github.com/jaypipes/procession/proto"

    "github.com/jaypipes/procession/pkg/iam/db"
)

func emptyOrganization() *pb.Organization {
    return &pb.Organization{}
}

// GetOrganization looks up a organization record by organization identifier and returns the
// Organization protobuf message for the organization
func (s *Server) GetOrganization(
    ctx context.Context,
    request *pb.GetOrganizationRequest,
) (*pb.Organization, error) {
    search := request.Search
    debug("> GetOrganization(%v)", search)

    organization, err := db.GetOrganization(s.Db, search)
    if err != nil {
        return nil, err
    }
    debug("< %v", organization)
    return organization, nil
}
