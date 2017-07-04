package context

import (
    "database/sql"

    "github.com/jaypipes/procession/pkg/authz"
    "github.com/jaypipes/procession/pkg/logging"
    "github.com/jaypipes/procession/pkg/events"
)

type Context struct {
    Db *sql.DB
    Events *events.Events
    Authz *authz.Authz
    Log *logging.Logs
}

func (ctx *Context) Close() {
    if ctx.Db != nil {
        ctx.Db.Close()
    }
}

func New() *Context {
    ctx := &Context{
        Log: logging.New(),
    }
    return ctx
}
