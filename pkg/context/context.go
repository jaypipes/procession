package context

import (
    "database/sql"
    "fmt"
    "log"
    "os"

    "github.com/jaypipes/procession/pkg/cfg"
    "github.com/jaypipes/procession/pkg/events"
)

type contextLogs struct {
    tlog *log.Logger
    ilog *log.Logger
    elog *log.Logger
}

type Context struct {
    Db *sql.DB
    Events *events.Events
    logs *contextLogs
}

func New() *Context {
    logs := &contextLogs{
        tlog: log.New(
            os.Stdout,
            "TRACE: ",
            (log.Ldate | log.Lmicroseconds | log.LUTC | log.Lshortfile),
        ),
        ilog: log.New(
            os.Stdout,
            "",
            (log.Ldate | log.Ltime | log.LUTC),
        ),
        elog: log.New(
            os.Stderr,
            "ERROR: ",
            (log.Ldate | log.Ltime | log.LUTC),
        ),
    }
    ctx := &Context{
        logs: logs,
    }
    return ctx
}

func (ctx *Context) Close() {
    if ctx.Db != nil {
        ctx.Db.Close()
    }
}

func (ctx *Context) Debug(message string, args ...interface{}) {
    if ctx.logs.tlog == nil {
        return
    }
    if cfg.LogLevel() > 1 {
        // Since we're logging calling file, the 3 below jumps us out of this
        // function so the file and line numbers will refer to the caller of
        // Context.Debug(), not this function itself.
        ctx.logs.tlog.Output(3, fmt.Sprintf(message, args...))
    }
}

func (ctx *Context) Info(message string, args ...interface{}) {
    if ctx.logs.ilog == nil {
        return
    }
    if cfg.LogLevel() > 0 {
        ctx.logs.ilog.Printf(message, args...)
    }
}
