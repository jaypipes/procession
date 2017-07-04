package logging

import (
    "fmt"
    "log"
    "os"
)

type Config struct {
    Level int
}

type Logs struct {
    cfg *Config
    log3 *log.Logger
    log2 *log.Logger
    log1 *log.Logger
    elog *log.Logger
    section string
}

func New() *Logs {
    logs := &Logs{
        cfg: &Config{
            Level: 0,
        },
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
    return logs
}

// Sets a scoped log section and returns a functor that should be deferred that
// resets the log section to its previous scope
func (logs *Logs) WithSection(section string) func() {
    curScopeSection := logs.section
    reset := func() {
        logs.section = curScopeSection
    }
    logs.section = section
    return reset
}

func (logs *Logs) SQL(sql string, args ...interface{}) {
    if logs.log3 == nil || logs.cfg.Level <= 2 {
        return
    }
    message := "== SQL START =="
    if logs.section != "" {
        message = fmt.Sprintf("[%s] %s", logs.section, message)
    }
    message = message + sql
    // Since we're logging calling file, the 2 below jumps us out of this
    // function so the file and line numbers will refer to the caller of
    // Context.Trace(), not this function itself.
    logs.log3.Output(2, message)
    footer := "== SQL END =="
    if logs.section != "" {
        footer = fmt.Sprintf("[%s] %s", logs.section, footer)
    }
    logs.log3.Output(2, footer)
}

func (logs *Logs) L3(message string, args ...interface{}) {
    if logs.log3 == nil || logs.cfg.Level <= 2 {
        return
    }
    if logs.section != "" {
        message = fmt.Sprintf("[%s] %s", logs.section, message)
    }
    // Since we're logging calling file, the 2 below jumps us out of this
    // function so the file and line numbers will refer to the caller of
    // Context.Trace(), not this function itself.
    logs.log3.Output(2, fmt.Sprintf(message, args...))
}

func (logs *Logs) L2(message string, args ...interface{}) {
    if logs.log2 == nil || logs.cfg.Level <= 1 {
        return
    }
    if logs.section != "" {
        message = fmt.Sprintf("[%s] %s", logs.section, message)
    }
    logs.log2.Printf(message, args...)
}

func (logs *Logs) L1(message string, args ...interface{}) {
    if logs.log1 == nil || logs.cfg.Level <= 0 {
        return
    }
    if logs.section != "" {
        message = fmt.Sprintf("[%s] %s", logs.section, message)
    }
    logs.log1.Printf(message, args...)
}

func (logs *Logs) ERR(message string, args ...interface{}) {
    if logs.elog == nil {
        return
    }
    if logs.section != "" {
        message = fmt.Sprintf("[%s] %s", logs.section, message)
    }
    logs.elog.Printf(message, args...)
}

