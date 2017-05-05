package db

import (
    "log"
    "net"
    "syscall"

    "database/sql"
    "github.com/go-sql-driver/mysql"
    "github.com/cenkalti/backoff"

    "github.com/jaypipes/procession/pkg/cfg"
)

// Returns a handle to the IAM database. Uses an exponential backoff retry
// strategy so that this can be run early in a service's startup code and we
// will wait for DB connectivity to materialize if not there initially.
func New() (*sql.DB, error) {
    var err error
    var db *sql.DB

    dsn := dbDsn()
    if db, err = sql.Open("mysql", dsn); err != nil {
        // NOTE(jaypipes): sql.Open() doesn't actually connect to the DB or
        // anything, so any error here is likely an OOM error and so fatal...
        return nil, err
    }
    connTimeout := cfg.ConnectTimeout()
    debug("connecting to DB (w/ %s overall timeout).", connTimeout.String())

    fatal := false

    bo := backoff.NewExponentialBackOff()
    bo.MaxElapsedTime = connTimeout

    fn := func() error {
        err = db.Ping()
        if err != nil {
            switch t := err.(type) {
                case *mysql.MySQLError:
                    dbErr := err.(*mysql.MySQLError)
                    if dbErr.Number == 1045 {
                        // Access denied for user
                        fatal = true
                        return err
                    }
                    if dbErr.Number == 1049 {
                        // Unknown database
                        fatal = true
                        return err
                    }
                case *net.OpError:
                    oerr := err.(*net.OpError)
                    if oerr.Temporary() || oerr.Timeout() {
                        // Each of these scenarios are errors that we can retry
                        // the operation. Services may come up in different
                        // order and we don't want to require a specific order
                        // of startup...
                        return err
                    }
                    if t.Op == "dial" {
                        destAddr := oerr.Addr
                        if destAddr == nil {
                            // Unknown host... probably a DNS failure and not
                            // something we're going to be able to recover from in
                            // a retry, so bail out
                            fatal = true
                        }
                        // If not unknown host, most likely a dial: tcp
                        // connection refused. In that case, let's retry. DB
                        // may not have been brought up before this service.
                        return err
                    } else if t.Op == "read" {
                        // Connection refused. This is an error we can backoff
                        // and retry in case the application started before the
                        // DB.
                        return err
                    }
                case syscall.Errno:
                    if t == syscall.ECONNREFUSED {
                        // Connection refused. This is an error we can backoff
                        // and retry in case the application started before the
                        // DB.
                        return err
                    }
                default:
                    debug("got unrecoverable %T error: %v attempting to " +
                          "connect to DB", err, err)
                    fatal = true
                    return err
            }
        }
        return nil
    }

    ticker := backoff.NewTicker(bo)

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
        log.Printf("[iam/db] debug: " + message, args...)
    }
}

func info(message string, args ...interface{}) {
    if cfg.LogLevel() > 0 {
        log.Printf("[iam/db] " + message, args...)
    }
}
