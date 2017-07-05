package storage

import (
    "errors"
    "time"

    "database/sql"

    "github.com/jaypipes/procession/pkg/events"
    "github.com/jaypipes/procession/pkg/logging"
    "github.com/jaypipes/procession/pkg/sqlutil"
)

var (
    ERR_CONCURRENT_UPDATE = errors.New("Another thread updated this record concurrently. Please try your update again after refreshing your view of it.")
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
    reset := s.log.WithSection("iam/storage")
    defer reset()
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
