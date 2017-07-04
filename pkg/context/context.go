package context

import (
    "database/sql"

    "github.com/jaypipes/procession/pkg/authz"
    "github.com/jaypipes/procession/pkg/logging"
    "github.com/jaypipes/procession/pkg/events"
)

type Context struct {
    Storage *sql.DB
    Events *events.Events
    Authz *authz.Authz
    Log *logging.Logs
}

func (ctx *Context) Close() {
    if ctx.Storage != nil {
        ctx.Storage.Close()
    }
}

func New() *Context {
    ctx := &Context{
        Log: logging.New(),
    }
    return ctx
}
