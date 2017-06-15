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
    log3 *log.Logger
    log2 *log.Logger
    log1 *log.Logger
    log0 *log.Logger
    section string
}

type Context struct {
    Db *sql.DB
    Events *events.Events
    logs *contextLogs
}

func New() *Context {
    logs := &contextLogs{
        log3: log.New(
            os.Stdout,
            "TRACE: ",
            (log.Ldate | log.Lmicroseconds | log.LUTC | log.Lshortfile),
        ),
        log2: log.New(
            os.Stdout,
            "",
            (log.Ldate | log.Ltime | log.LUTC),
        ),
        log1: log.New(
            os.Stdout,
            "",
            (log.Ldate | log.Ltime | log.LUTC),
        ),
        log0: log.New(
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

func (ctx *Context) L3(message string, args ...interface{}) {
    if ctx.logs.log3 == nil {
        return
    }
    if cfg.LogLevel() > 2 {
        if ctx.logs.section != "" {
            message = fmt.Sprintf("[%s] %s", ctx.logs.section, message)
        }
        // Since we're logging calling file, the 3 below jumps us out of this
        // function so the file and line numbers will refer to the caller of
        // Context.Trace(), not this function itself.
        ctx.logs.log3.Output(2, fmt.Sprintf(message, args...))
    }
}

func (ctx *Context) L2(message string, args ...interface{}) {
    if ctx.logs.log3 == nil {
        return
    }
    if cfg.LogLevel() > 1 {
        if ctx.logs.section != "" {
            message = fmt.Sprintf("[%s] %s", ctx.logs.section, message)
        }
        ctx.logs.log2.Printf(message, args...)
    }
}

func (ctx *Context) L1(message string, args ...interface{}) {
    if ctx.logs.log1 == nil {
        return
    }
    if cfg.LogLevel() > 0 {
        if ctx.logs.section != "" {
            message = fmt.Sprintf("[%s] %s", ctx.logs.section, message)
        }
        ctx.logs.log1.Printf(message, args...)
    }
}

func (ctx *Context) L0(message string, args ...interface{}) {
    if ctx.logs.log1 == nil {
        return
    }
    if ctx.logs.section != "" {
        message = fmt.Sprintf("[%s] %s", ctx.logs.section, message)
    }
    ctx.logs.log0.Printf(message, args...)
}
