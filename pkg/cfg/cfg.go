package cfg

/*
    Configuration of Procession services can be done via either command line
    options (flags) or via environment variables.
    
    *Some* environment variables, e.g. PROCESSION_LOG_LEVEL,  may be changed
    **after** a service is started, and the value of the environment variable
    will override anything that had initially been provided via a command line
    option.
*/

import (
    "time"

    flag "github.com/ogier/pflag"
    "github.com/jaypipes/procession/pkg/env"
)

const (
    defaultLogLevel = 0
    defaultConnectTimeoutSeconds = 60
)

var (
    optLogLevel = flag.Int(
        "log-level",
        env.EnvOrDefaultInt(
            "PROCESSION_LOG_LEVEL", defaultLogLevel,
        ),
        "The verbosity of logging. 0 (default) = virtually no logging. " +
        "1 = some logging. 2 = debug-level logging",
    )
    optConnectTimeoutSeconds = flag.Int(
        "connect-timeout",
        env.EnvOrDefaultInt(
            "PROCESSION_CONNECT_TIMEOUT_SECONDS", defaultConnectTimeoutSeconds,
        ),
        "Number of seconds to wait while attempting to initially make a " +
        "connection to some external or dependent service",
    )
)

// Returns the logging level.
func LogLevel() int {
    return env.EnvOrDefaultInt(
        "PROCESSION_LOG_LEVEL",
        *optLogLevel,
    )
}

func ConnectTimeout() time.Duration {
    return time.Duration(
        env.EnvOrDefaultInt(
            "PROCESSION_CONNECT_TIMEOUT_SECONDS",
            *optConnectTimeoutSeconds,
        ),
    ) * time.Second
}

func ParseCliOpts() {
    flag.Parse()
}
