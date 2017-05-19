package rpc

import (
    "database/sql"
    "fmt"

    "golang.org/x/net/context"

    pb "github.com/jaypipes/procession/proto"

    "github.com/jaypipes/procession/pkg/iam/db"
)

// OrganizationList looks up zero or more organization records matching
// supplied filters and streams Organization messages back to the caller
func (s *Server) OrganizationList(
    req *pb.OrganizationListRequest,
    stream pb.IAM_OrganizationListServer,
) error {
    orgRows, err := db.OrganizationList(s.Db, req.Filters)
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

// OrganizationGet looks up a organization record by organization identifier
// and returns the Organization protobuf message for the organization
func (s *Server) OrganizationGet(
    ctx context.Context,
    req *pb.OrganizationGetRequest,
) (*pb.Organization, error) {
    organization, err := db.OrganizationGet(s.Db, req.Search)
    if err != nil {
        return nil, err
    }
    return organization, nil
}

// OrganizationSet creates a new organization or updates an existing
// organization
func (s *Server) OrganizationSet(
    ctx context.Context,
    req *pb.OrganizationSetRequest,
) (*pb.OrganizationSetResponse, error) {
    changed := req.Changed
    if req.Search == nil {
        newOrg, err := db.OrganizationCreate(
            req.Session,
            s.Db,
            changed,
        )
        if err != nil {
            return nil, err
        }
        resp := &pb.OrganizationSetResponse{
            Organization: newOrg,
        }
        return resp, nil
    }
    before, err := db.OrganizationGet(s.Db, req.Search.Value)
    if err != nil {
        return nil, err
    }
    if before.Uuid == "" {
        notFound := fmt.Errorf("No such organization found.")
        return nil, notFound
    }

    newOrg, err := db.OrganizationUpdate(s.Db, before, changed)
    if err != nil {
        return nil, err
    }
    resp := &pb.OrganizationSetResponse{
        Organization: newOrg,
    }
    return resp, nil
}
