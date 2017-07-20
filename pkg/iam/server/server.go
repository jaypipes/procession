package server

import (
    "errors"
    "fmt"

    "github.com/jaypipes/gsr"

    "github.com/jaypipes/procession/pkg/authz"
    "github.com/jaypipes/procession/pkg/events"
    "github.com/jaypipes/procession/pkg/logging"

    "github.com/jaypipes/procession/pkg/iam/iamstorage"
)

var (
    ERR_FORBIDDEN = errors.New("User is not authorized to perform that action")
)

type Server struct {
    log *logging.Logs
    cfg *Config
    authz *authz.Authz
    registry *gsr.Registry
    storage *iamstorage.IAMStorage
    events *events.Events
}

func (s *Server) Close() {
    if s.storage != nil {
        s.storage.Close()
    }
}

func New(
    cfg *Config,
    log *logging.Logs,
) (*Server, error) {
    defer log.WithSection("iam/server")()

    registry, err := gsr.New()
    if err != nil {
        return nil, fmt.Errorf("failed to create gsr.Registry object: %v", err)
    }
    log.L2("connected to gsr service registry.")

    storagecfg := &iamstorage.Config{
        DSN: cfg.DSN,
        ConnectTimeoutSeconds: 60,
    }

    storage, err := iamstorage.New(storagecfg, log)
    if err != nil {
        return nil, fmt.Errorf("failed to connect to IAM data storage: %v", err)
    }
    log.L2("connected to DB.")

    authz, err := authz.NewWithStorage(log, storage)
    if err != nil {
        return nil, fmt.Errorf("failed to instantiate authz: %v", err)
    }
    log.L2("auth system initialized.")

    // Register this IAM service endpoint with the service registry
    addr := fmt.Sprintf("%s:%d", cfg.BindHost, cfg.BindPort)
    ep := gsr.Endpoint{
        Service: &gsr.Service{cfg.ServiceName},
        Address: addr,
    }
    err = registry.Register(&ep)
    if err != nil {
        log.ERR("unable to register %v with gsr: %v", ep, err)
    }
    log.L2(
        "registered %s service endpoint running at %s with gsr.",
        cfg.ServiceName,
        addr,
    )

    s := &Server{
        log: log,
        cfg: cfg,
        authz: authz,
        registry: registry,
        storage: storage,
    }
    return s, nil
}
