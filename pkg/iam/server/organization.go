package server

import (
    "database/sql"
    "fmt"

    "golang.org/x/net/context"

    pb "github.com/jaypipes/procession/proto"
    "github.com/jaypipes/procession/pkg/errors"
)

// OrganizationList looks up zero or more organization records matching
// supplied filters and streams Organization messages back to the caller
func (s *Server) OrganizationList(
    req *pb.OrganizationListRequest,
    stream pb.IAM_OrganizationListServer,
) error {
    defer s.log.WithSection("iam/server")()

    if ! s.authz.Check(req.Session, pb.Permission_READ_ORGANIZATION) {
        return errors.FORBIDDEN
    }

    s.log.L3("Listing organizations")

    orgRows, err := s.storage.OrganizationList(req.Filters)
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

// OrganizationGet looks up a organization record by organization identifier
// and returns the Organization protobuf message for the organization
func (s *Server) OrganizationGet(
    ctx context.Context,
    req *pb.OrganizationGetRequest,
) (*pb.Organization, error) {
    defer s.log.WithSection("iam/server")()

    s.log.L3("Getting organization %s", req.Search)

    organization, err := s.storage.OrganizationGet(req.Search)
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
    defer s.log.WithSection("iam/server")()

    search := req.Search

    s.log.L3("Deleting organization %s", search)

    sess := req.Session
    err := s.storage.OrganizationDelete(sess, search)
    if err != nil {
        return nil, err
    }
    s.log.L1("Deleted organization %s", search)
    return &pb.OrganizationDeleteResponse{NumDeleted: 1}, nil
}

// OrganizationSet creates a new organization or updates an existing
// organization
func (s *Server) OrganizationSet(
    ctx context.Context,
    req *pb.OrganizationSetRequest,
) (*pb.OrganizationSetResponse, error) {
    defer s.log.WithSection("iam/server")()

    changed := req.Changed

    if req.Search == nil {
        s.log.L3("Creating new organization")

        newOrg, err := s.storage.OrganizationCreate(
            req.Session,
            changed,
        )
        if err != nil {
            return nil, err
        }
        resp := &pb.OrganizationSetResponse{
            Organization: newOrg,
        }
        s.log.L1("Created new organization %s", newOrg.Uuid)
        return resp, nil
    }

    s.log.L3("Updating organization %s", req.Search.Value)

    before, err := s.storage.OrganizationGet(req.Search.Value)
    if err != nil {
        return nil, err
    }
    if before.Uuid == "" {
        notFound := fmt.Errorf("No such organization found.")
        return nil, notFound
    }

    newOrg, err := s.storage.OrganizationUpdate(before, changed)
    if err != nil {
        return nil, err
    }
    resp := &pb.OrganizationSetResponse{
        Organization: newOrg,
    }
    s.log.L1("Updated organization %s", newOrg.Uuid)
    return resp, nil
}

// Add or remove users from an organization
func (s *Server) OrganizationMembersSet(
    ctx context.Context,
    req *pb.OrganizationMembersSetRequest,
) (*pb.OrganizationMembersSetResponse, error) {
    defer s.log.WithSection("iam/server")()

    added, removed, err := s.storage.OrganizationMembersSet(req)
    if err != nil {
        return nil, err
    }
    resp := &pb.OrganizationMembersSetResponse{
        NumAdded: added,
        NumRemoved: removed,
    }
    s.log.L1(
        "Updated membership for organization %s (add %d, remove %d members)",
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
    defer s.log.WithSection("iam/server")()

    userRows, err := s.storage.OrganizationMembersList(req)
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
