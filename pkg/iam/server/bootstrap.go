package server

import (
    "fmt"

    "golang.org/x/net/context"

    pb "github.com/jaypipes/procession/proto"
)

// Bootstrap checks a bootstrap key and creates a user with SUPER privileges
func (s *Server) Bootstrap(
    ctx context.Context,
    req *pb.BootstrapRequest,
) (*pb.BootstrapResponse, error) {
    // The default value of the bootstrap key CLI/env option is "" which means
    // the Procession service has to be explcitly started with a
    // --bootstrap-key value in order for bootstrap operations, which don't
    // check for any authentication/authorization, to be taken.
    if s.cfg.BootstrapKey == "" {
        return nil, fmt.Errorf("Invalid bootstrap key")
    }

    key := req.Key
    if key == "" {
        return nil, fmt.Errorf("Invalid bootstrap key")
    }
    if key != s.cfg.BootstrapKey {
        return nil, fmt.Errorf("Invalid bootstrap key")
    }

    defer s.log.WithSection("iam/server")()

    // Create a role with the SUPER privilege if one with the requested name
    // does not exist
    role, err := s.storage.RoleGet(req.SuperRoleName)
    if err != nil {
        return nil, err
    }
    if role.Uuid == "" {
        rsFields := &pb.RoleSetFields{
            DisplayName: &pb.StringValue{
                Value: req.SuperRoleName,
            },
            Add: []pb.Permission{pb.Permission_SUPER},
        }
        _, err := s.storage.RoleCreate(nil, rsFields)
        if err != nil {
            return nil, err
        }
        s.log.L1("Created role %s with SUPER privilege", req.SuperRoleName)
    }

    // Add user records for each email in the collection of super user emails
    for _, email := range req.SuperUserEmails {
        user, err := s.storage.UserGet(email)
        if err != nil {
            return nil, err
        }
        if user.Uuid == "" {
            newFields := &pb.UserSetFields{
                DisplayName: &pb.StringValue{
                    Value: email,
                },
                Email: &pb.StringValue{
                    Value: email,
                },
            }
            user, err = s.storage.UserCreate(newFields)
            if err != nil {
                return nil, err
            }
            // Add the new super user to the super role
            ursReq := &pb.UserRolesSetRequest{
                User: email,
                Add: []string{req.SuperRoleName},
            }
            _, _, err := s.storage.UserRolesSet(ursReq)
            if err != nil {
                return nil, err
            }
            s.log.L1("Created new super user %s (%s)", email, user.Uuid)
        }
    }

    s.log.L1("Successful bootstrap operation.")

    // Clear the bootstrap key to effectively make this a one-time operation
    // TODO(jaypipes): Determine whether the affect of this reset in a
    // multi-server environment is something we should care about?
    s.cfg.BootstrapKey = ""
    return &pb.BootstrapResponse{KeyReset: true}, nil
}
