package rpc

import (
    "database/sql"
    "log"

    "github.com/jaypipes/procession/pkg/cfg"
)

type Server struct {
    Db *sql.DB
}

func debug(message string, args ...interface{}) {
    if cfg.LogLevel() > 1 {
        log.Printf("[iam] debug: " + message, args...)
    }
}

func info(message string, args ...interface{}) {
    if cfg.LogLevel() > 0 {
        log.Printf("[iam] " + message, args...)
    }
}
