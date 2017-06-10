package context

import (
    "database/sql"
    "log"

    "github.com/jaypipes/procession/pkg/cfg"
    "github.com/jaypipes/procession/pkg/events"
)

type Context struct {
    Log *log.Logger
    Db *sql.DB
    Events *events.Events
}

func (ctx *Context) Close() {
    if ctx.Db != nil {
        ctx.Db.Close()
    }
}

func (ctx *Context) Debug(message string, args ...interface{}) {
    if cfg.LogLevel() > 1 {
        ctx.Log.Printf("debug: " + message, args...)
    }
}

func (ctx *Context) Info(message string, args ...interface{}) {
    if cfg.LogLevel() > 0 {
        ctx.Log.Printf(message, args...)
    }
}
