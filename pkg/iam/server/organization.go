package server

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
    log := s.Ctx.Log
    reset := log.WithSection("iam/server")
    defer reset()

    log.L3("Listing organizations")

    orgRows, err := db.OrganizationList(s.Ctx, req.Filters)
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
    log := s.Ctx.Log
    reset := log.WithSection("iam/server")
    defer reset()

    log.L3("Getting organization %s", req.Search)

    organization, err := db.OrganizationGet(s.Ctx, req.Search)
    if err != nil {
        return nil, err
    }
    return organization, nil
}

// Deletes an organization, all of its owned resources and membership records
func (s *Server) OrganizationDelete(
    ctx context.Context,
    req *pb.OrganizationDeleteRequest,
) (*pb.OrganizationDeleteResponse, error) {
    log := s.Ctx.Log
    reset := log.WithSection("iam/server")
    defer reset()
    search := req.Search

    log.L3("Deleting organization %s", search)

    sess := req.Session
    err := db.OrganizationDelete(s.Ctx, sess, search)
    if err != nil {
        return nil, err
    }
    log.L1("Deleted organization %s", search)
    return &pb.OrganizationDeleteResponse{NumDeleted: 1}, nil
}

// OrganizationSet creates a new organization or updates an existing
// organization
func (s *Server) OrganizationSet(
    ctx context.Context,
    req *pb.OrganizationSetRequest,
) (*pb.OrganizationSetResponse, error) {
    log := s.Ctx.Log
    reset := log.WithSection("iam/server")
    defer reset()
    changed := req.Changed

    if req.Search == nil {
        log.L3("Creating new organization")

        newOrg, err := db.OrganizationCreate(
            req.Session,
            s.Ctx,
            changed,
        )
        if err != nil {
            return nil, err
        }
        resp := &pb.OrganizationSetResponse{
            Organization: newOrg,
        }
        log.L1("Created new organization %s", newOrg.Uuid)
        return resp, nil
    }

    log.L3("Updating organization %s", req.Search.Value)

    before, err := db.OrganizationGet(s.Ctx, req.Search.Value)
    if err != nil {
        return nil, err
    }
    if before.Uuid == "" {
        notFound := fmt.Errorf("No such organization found.")
        return nil, notFound
    }

    newOrg, err := db.OrganizationUpdate(s.Ctx, before, changed)
    if err != nil {
        return nil, err
    }
    resp := &pb.OrganizationSetResponse{
        Organization: newOrg,
    }
    log.L1("Updated organization %s", newOrg.Uuid)
    return resp, nil
}

// Add or remove users from an organization
func (s *Server) OrganizationMembersSet(
    ctx context.Context,
    req *pb.OrganizationMembersSetRequest,
) (*pb.OrganizationMembersSetResponse, error) {
    log := s.Ctx.Log
    reset := log.WithSection("iam/server")
    defer reset()
    added, removed, err := db.OrganizationMembersSet(s.Ctx, req)
    if err != nil {
        return nil, err
    }
    resp := &pb.OrganizationMembersSetResponse{
        NumAdded: added,
        NumRemoved: removed,
    }
    log.L1("Updated membership for organization %s " +
           "(added %d, removed %d members)",
         req.Organization,
         added,
         removed,
    )
    return resp, nil
}

// Return the users in an organization
func (s *Server) OrganizationMembersList(
    req *pb.OrganizationMembersListRequest,
    stream pb.IAM_OrganizationMembersListServer,
) error {
    log := s.Ctx.Log
    reset := log.WithSection("iam/server")
    defer reset()
    userRows, err := db.OrganizationMembersList(s.Ctx, req)
    if err != nil {
        return err
    }
    defer userRows.Close()
    for userRows.Next() {
        user := pb.User{}
        err := userRows.Scan(
            &user.Uuid,
            &user.DisplayName,
            &user.Email,
            &user.Slug,
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
