package server

import (
    "fmt"

    "github.com/jaypipes/gsr"

    "github.com/jaypipes/procession/pkg/authz"
    "github.com/jaypipes/procession/pkg/context"
    "github.com/jaypipes/procession/pkg/logging"

    "github.com/jaypipes/procession/pkg/iam/storage"
)

type Server struct {
    log *logging.Logs
    ctx *context.Context
    Config *Config
    Registry *gsr.Registry
    storage *storage.Storage
}

func New(ctx *context.Context) (*Server, error) {
    log := ctx.Log
    reset := log.WithSection("iam/server")
    defer reset()

    cfg := configFromOpts()

    registry, err := gsr.New()
    if err != nil {
        return nil, fmt.Errorf("failed to create gsr.Registry object: %v", err)
    }
    log.L2("connected to gsr service registry.")

    storagecfg := &storage.Config{
        DSN: cfg.DSN,
        ConnectTimeoutSeconds: 60,
    }

    storage, err := storage.New(storagecfg, log)
    if err != nil {
        return nil, fmt.Errorf("failed to connect to IAM data storage: %v", err)
    }
    log.L2("connected to DB.")

    authz, err := authz.New()
    if err != nil {
        return nil, fmt.Errorf("failed to instantiate authz: %v", err)
    }
    ctx.Authz = authz
    log.L2("auth system initialized.")

    s := &Server{
        log: log,
        ctx: ctx,
        Config: cfg,
        Registry: registry,
        storage: storage,
    }
    return s, nil
}
