package iamdb

import (
    flag "github.com/ogier/pflag"

    "github.com/jaypipes/procession/pkg/env"
)

const (
    defaultDbDsn = "user:password@/dbname"
)

var (
    optDbDsn = flag.String(
        "dsn",
        env.EnvOrDefaultStr(
            "PROCESSION_DB_DSN", defaultDbDsn,
        ),
        "Data Source Name (DSN) for connecting to the SQL data store",
    )
)

// Returns the DSN to use for connecting to the SQL data store
func dbDsn() string {
    return env.EnvOrDefaultStr(
        "PROCESSION_DB_DSN",
        *optDbDsn,
    )
}
