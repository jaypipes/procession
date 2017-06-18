package server

import (
    "fmt"

    "github.com/jaypipes/gsr"

    "github.com/jaypipes/procession/pkg/context"

    "github.com/jaypipes/procession/pkg/iam/db"
)

type Server struct {
    Ctx *context.Context
    Config *Config
    Registry *gsr.Registry
}

func New(ctx *context.Context) (*Server, error) {
    reset := ctx.LogSection("iam/server")
    defer reset()

    cfg := configFromOpts()

    registry, err := gsr.New()
    if err != nil {
        return nil, fmt.Errorf("failed to create gsr.Registry object: %v", err)
    }
    ctx.L2("connected to gsr service registry.")

    db, err := db.New(ctx)
    if err != nil {
        return nil, fmt.Errorf("failed to ping iam database: %v", err)
    }
    ctx.Db = db
    ctx.L2("connected to DB.")

    s := &Server{
        Ctx: ctx,
        Config: cfg,
        Registry: registry,
    }
    return s, nil
}