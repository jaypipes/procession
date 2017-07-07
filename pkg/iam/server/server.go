package server

import (
    "fmt"

    "github.com/jaypipes/gsr"

    "github.com/jaypipes/procession/pkg/authz"
    "github.com/jaypipes/procession/pkg/events"
    "github.com/jaypipes/procession/pkg/logging"

    "github.com/jaypipes/procession/pkg/iam/iamstorage"
)

type Server struct {
    log *logging.Logs
    cfg *Config
    authz *authz.Authz
    Registry *gsr.Registry
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

    authz, err := authz.New()
    if err != nil {
        return nil, fmt.Errorf("failed to instantiate authz: %v", err)
    }
    log.L2("auth system initialized.")

    s := &Server{
        log: log,
        cfg: cfg,
        authz: authz,
        Registry: registry,
        storage: storage,
    }
    return s, nil
}
