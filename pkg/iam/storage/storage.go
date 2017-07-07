package storage

import (
    "time"

    "database/sql"

    "github.com/jaypipes/procession/pkg/events"
    "github.com/jaypipes/procession/pkg/logging"
    "github.com/jaypipes/procession/pkg/storage"
    "github.com/jaypipes/procession/pkg/sqlutil"
)

type Config struct {
    DSN string
    ConnectTimeoutSeconds int
}

func (cfg *Config) ConnectTimeout() time.Duration {
    return time.Duration(cfg.ConnectTimeoutSeconds) * time.Second
}

type Storage struct {
    cfg *Config
    log *logging.Logs
    db *sql.DB
    events *events.Events
}

func (s *Storage) Close() {
    if s.db != nil {
        s.db.Close()
    }
}

func (s *Storage) Rows(
    qs string,
    qargs ...interface{},
) (storage.RowIterator, error) {
    defer s.log.WithSection("iam/storage")()

    s.log.SQL(qs)

    rows, err := s.db.Query(qs, qargs...)
    if err != nil {
        return nil, err
    }
    err = rows.Err()
    if err != nil {
        return nil, err
    }
    return rows, nil
}

func New(
    cfg *Config,
    log *logging.Logs,
) (*Storage, error) {
    s := &Storage{
        cfg: cfg,
        log: log,
    }
    if err := s.connect(); err != nil {
        return nil, err
    }
    return s, nil
}

// Attempts to connect to the backend IAM database. Uses an exponential backoff
// retry strategy so that this can be run early in a service's startup code and
// we will wait for DB connectivity to materialize if not there initially.
func (s *Storage) connect() error {
    defer s.log.WithSection("iam/storage")()
    var err error
    var db *sql.DB

    dsn := s.cfg.DSN
    if db, err = sql.Open("mysql", dsn); err != nil {
        // NOTE(jaypipes): sql.Open() doesn't actually connect to the DB or
        // anything, so any error here is likely an OOM error and so fatal...
        return err
    }
    connTimeout := s.cfg.ConnectTimeout()
    s.log.L2("connecting to DB (w/ %s overall timeout).", connTimeout.String())

    err = sqlutil.Ping(db, connTimeout)
    if err != nil {
        return err
    }

    s.db = db
    return nil
}
