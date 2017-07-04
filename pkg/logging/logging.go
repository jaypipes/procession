package logging

import (
    "fmt"
    "log"
    "os"

    flag "github.com/ogier/pflag"

    "github.com/jaypipes/procession/pkg/env"
)

const (
    defaultLogLevel = 0
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

func New(cfg *Config) *Logs {
    logs := &Logs{
        cfg: cfg,
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

// Returns a new Config struct populated with the configuration values read
// from the command line or environment variables
func ConfigFromOpts() *Config {
    level := flag.Int(
        "log-level",
        env.EnvOrDefaultInt(
            "PROCESSION_LOG_LEVEL", defaultLogLevel,
        ),
        "The verbosity of logging. 0 (default) = virtually no logging. " +
        "1 = some logging. 2 = debug-level logging, 3 = trace-level logging",
    )

    flag.Parse()
    cfg := &Config{
        Level: *level,
    }
    return cfg
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

