package iamstorage

import (
	"github.com/jaypipes/procession/pkg/events"
	"github.com/jaypipes/procession/pkg/logging"
	"github.com/jaypipes/procession/pkg/storage"
)

type Config struct {
	DSN                   string
	ConnectTimeoutSeconds int
}

type IAMStorage struct {
	*storage.Storage
	log    *logging.Logs
	events *events.Events
}

func New(
	cfg *Config,
	log *logging.Logs,
) (*IAMStorage, error) {
	scfg := &storage.Config{
		DSN: cfg.DSN,
		ConnectTimeoutSeconds: cfg.ConnectTimeoutSeconds,
	}
	s, err := storage.New(scfg, log)
	if err != nil {
		return nil, err
	}
	return &IAMStorage{s, log, nil}, nil
}
