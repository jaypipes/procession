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

    s.log.L1("Successful bootstrap operation.")

    // Clear the bootstrap key to effectively make this a one-time operation
    // TODO(jaypipes): Determine whether the affect of this reset in a
    // multi-server environment is something we should care about?
    s.cfg.BootstrapKey = ""
    return &pb.BootstrapResponse{KeyReset: true}, nil
}
