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
    dlog *log.Logger
    ilog *log.Logger
    elog *log.Logger
    section string
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
        dlog: log.New(
            os.Stdout,
            "",
            (log.Ldate | log.Ltime | log.LUTC),
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
        section: "",
    }
    ctx := &Context{
        logs: logs,
    }
    return ctx
}

// Sets a scoped log section and returns a functor that should be deferred that resets the log section to its previous scope
func (ctx *Context) LogSection(section string) func() {
    curScopeSection := ctx.logs.section
    reset := func() {
        ctx.logs.section = curScopeSection
    }
    ctx.logs.section = section
    return reset
}

func (ctx *Context) Close() {
    if ctx.Db != nil {
        ctx.Db.Close()
    }
}

func (ctx *Context) Trace(message string, args ...interface{}) {
    if ctx.logs.tlog == nil {
        return
    }
    if cfg.LogLevel() > 2 {
        if ctx.logs.section != "" {
            message = fmt.Sprintf("[%s] %s", ctx.logs.section, message)
        }
        // Since we're logging calling file, the 3 below jumps us out of this
        // function so the file and line numbers will refer to the caller of
        // Context.Trace(), not this function itself.
        ctx.logs.tlog.Output(3, fmt.Sprintf(message, args...))
    }
}

func (ctx *Context) Debug(message string, args ...interface{}) {
    if ctx.logs.tlog == nil {
        return
    }
    if cfg.LogLevel() > 1 {
        if ctx.logs.section != "" {
            message = fmt.Sprintf("[%s] %s", ctx.logs.section, message)
        }
        ctx.logs.dlog.Printf(message, args...)
    }
}

func (ctx *Context) Info(message string, args ...interface{}) {
    if ctx.logs.ilog == nil {
        return
    }
    if cfg.LogLevel() > 0 {
        if ctx.logs.section != "" {
            message = fmt.Sprintf("[%s] %s", ctx.logs.section, message)
        }
        ctx.logs.ilog.Printf(message, args...)
    }
}
