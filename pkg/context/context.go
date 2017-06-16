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
        log3: log.New(
            os.Stdout,
            "",
            (log.Ldate | log.Ltime | log.LUTC),
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

func (ctx *Context) LSQL(sql string, args ...interface{}) {
    if ctx.logs.log3 == nil || cfg.LogLevel() <= 2 {
        return
    }
    message := "== SQL START =="
    if ctx.logs.section != "" {
        message = fmt.Sprintf("[%s] %s", ctx.logs.section, message)
    }
    message = message + sql
    // Since we're logging calling file, the 2 below jumps us out of this
    // function so the file and line numbers will refer to the caller of
    // Context.Trace(), not this function itself.
    ctx.logs.log3.Output(2, message)
    footer := "== SQL END =="
    if ctx.logs.section != "" {
        footer = fmt.Sprintf("[%s] %s", ctx.logs.section, footer)
    }
    ctx.logs.log3.Output(2, footer)
}

func (ctx *Context) L3(message string, args ...interface{}) {
    if ctx.logs.log3 == nil || cfg.LogLevel() <= 2 {
        return
    }
    if ctx.logs.section != "" {
        message = fmt.Sprintf("[%s] %s", ctx.logs.section, message)
    }
    // Since we're logging calling file, the 2 below jumps us out of this
    // function so the file and line numbers will refer to the caller of
    // Context.Trace(), not this function itself.
    ctx.logs.log3.Output(2, fmt.Sprintf(message, args...))
}

func (ctx *Context) L2(message string, args ...interface{}) {
    if ctx.logs.log2 == nil || cfg.LogLevel() <= 1 {
        return
    }
    if ctx.logs.section != "" {
        message = fmt.Sprintf("[%s] %s", ctx.logs.section, message)
    }
    ctx.logs.log2.Printf(message, args...)
}

func (ctx *Context) L1(message string, args ...interface{}) {
    if ctx.logs.log1 == nil || cfg.LogLevel() <= 0 {
        return
    }
    if ctx.logs.section != "" {
        message = fmt.Sprintf("[%s] %s", ctx.logs.section, message)
    }
    ctx.logs.log1.Printf(message, args...)
}

func (ctx *Context) LERR(message string, args ...interface{}) {
    if ctx.logs.elog == nil {
        return
    }
    if ctx.logs.section != "" {
        message = fmt.Sprintf("[%s] %s", ctx.logs.section, message)
    }
    ctx.logs.elog.Printf(message, args...)
}
