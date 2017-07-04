package server

import (
    "fmt"

    "github.com/jaypipes/gsr"

    "github.com/jaypipes/procession/pkg/authz"
    "github.com/jaypipes/procession/pkg/context"

    "github.com/jaypipes/procession/pkg/iam/db"
)

type Server struct {
    Ctx *context.Context
    Config *Config
    Registry *gsr.Registry
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

    dbcfg := &db.Config{
        DSN: cfg.DSN,
        ConnectTimeoutSeconds: 60,
    }

    db, err := db.New(ctx, dbcfg)
    if err != nil {
        return nil, fmt.Errorf("failed to ping iam database: %v", err)
    }
    ctx.Db = db
    log.L2("connected to DB.")

    authz, err := authz.New()
    if err != nil {
        return nil, fmt.Errorf("failed to instantiate authz: %v", err)
    }
    ctx.Authz = authz
    log.L2("auth system initialized.")

    s := &Server{
        Ctx: ctx,
        Config: cfg,
        Registry: registry,
    }
    return s, nil
}
