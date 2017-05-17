package rpc

import (
    "database/sql"
    "fmt"

    "golang.org/x/net/context"

    pb "github.com/jaypipes/procession/proto"

    "github.com/jaypipes/procession/pkg/iam/db"
)

func emptyOrganization() *pb.Organization {
    return &pb.Organization{}
}

// ListOrganizations looks up zero or more organization records matching supplied filters and
// streams Organization messages back to the caller
func (s *Server) ListOrganizations(
    request *pb.ListOrganizationsRequest,
    stream pb.IAM_ListOrganizationsServer,
) error {
    filters := request.Filters
    debug("> ListOrganizations(%v)", filters)

    organizationRows, err := db.ListOrganizations(s.Db, filters)
    if err != nil {
        return err
    }
    defer organizationRows.Close()
    for organizationRows.Next() {
        organization := pb.Organization{}
        var parentUuid sql.NullString
        err := organizationRows.Scan(
            &organization.Uuid,
            &organization.DisplayName,
            &organization.Slug,
            &organization.Generation,
            &parentUuid,
        )
        if err != nil {
            return err
        }
        if parentUuid.Valid {
            sv := pb.StringValue{Value: parentUuid.String}
            organization.ParentOrganizationUuid = &sv
        }
        if err = stream.Send(&organization); err != nil {
            return err
        }
    }
    return nil
}

// GetOrganization looks up a organization record by organization identifier
// and returns the Organization protobuf message for the organization
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

// SetOrganization creates a new organization or updates an existing
// organization
func (s *Server) SetOrganization(
    ctx context.Context,
    request *pb.SetOrganizationRequest,
) (*pb.SetOrganizationResponse, error) {
    newFields := request.OrganizationFields
    if request.Search == nil {
        newOrganization, err := db.CreateOrganization(
            request.Session,
            s.Db,
            newFields,
        )
        if err != nil {
            return nil, err
        }
        resp := &pb.SetOrganizationResponse{
            Organization: newOrganization,
        }
        return resp, nil
    }
    before, err := db.GetOrganization(s.Db, request.Search.Value)
    if err != nil {
        return nil, err
    }
    if before.Uuid == "" {
        notFound := fmt.Errorf("No such organization found.")
        return nil, notFound
    }

    newOrganization, err := db.UpdateOrganization(s.Db, before, newFields)
    if err != nil {
        return nil, err
    }
    resp := &pb.SetOrganizationResponse{
        Organization: newOrganization,
    }
    return resp, nil
}
