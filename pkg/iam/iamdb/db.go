package iamdb

import (
    "log"

    "database/sql"
    _ "github.com/go-sql-driver/mysql"
    "github.com/cenkalti/backoff"

    "github.com/jaypipes/procession/pkg/cfg"
)

// Returns a handle to the IAM database. Uses an exponential backoff retry
// strategy so that this can be run early in a service's startup code and we
// will wait for DB connectivity to materialize if not there initially.
func NewDB(dsn string) (*sql.DB, error) {
    var err error
    var db *sql.DB

    if db, err = sql.Open("mysql", dsn); err != nil {
        // NOTE(jaypipes): sql.Open() doesn't actually connect to the DB or
        // anything, so any error here is likely an OOM error and so fatal...
        return nil, err
    }

    fatal := false

    bo := backoff.NewExponentialBackOff()
    bo.MaxElapsedTime = cfg.ConnectTimeout()

    fn := func() error {
        err = db.Ping()
        if err != nil {
            fatal = true
            return err
        }
        return nil
    }

    ticker := backoff.NewTicker(bo)

    debug("connecting to iam db.")
    attempts:= 0
    for _ = range ticker.C {
        if err = fn(); err != nil {
            attempts += 1
            if fatal {
                break
            }
            debug("failed to ping iam db: %v. retrying.", err)
            continue
        }

        ticker.Stop()
        break
    }

    if err != nil {
        debug("failed to ping iam db. final error reported: %v", err)
        debug("attempted %d times over %v. exiting.",
              attempts, bo.GetElapsedTime().String())
        return nil, err
    }
    return db, nil
}

func debug(message string, args ...interface{}) {
    if cfg.LogLevel() > 1 {
        log.Printf("[iamdb] debug: " + message, args...)
    }
}

func info(message string, args ...interface{}) {
    if cfg.LogLevel() > 0 {
        log.Printf("[iamdb] " + message, args...)
    }
}
