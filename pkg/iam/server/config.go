package server

import (
    "path/filepath"

    flag "github.com/ogier/pflag"

    "github.com/jaypipes/procession/pkg/cfg"
    "github.com/jaypipes/procession/pkg/env"
)

const (
    cfgPath = "/etc/procession/iam"
    defaultUseTLS = false
    defaultPort = 10000
)

var (
    defaultCertPath = filepath.Join(cfgPath, "server.pem")
    defaultKeyPath = filepath.Join(cfgPath, "server.key")
)

type Config struct {
    UseTLS bool
    CertPath string
    KeyPath string
    Port int
}

func configFromOpts() *Config {
    optUseTLS := flag.Bool(
        "tls",
        env.EnvOrDefaultBool(
            "PROCESSION_USE_TLS", defaultUseTLS,
        ),
        "Connection uses TLS if true, else plain TCP",
    )
    optCertPath := flag.String(
        "cert-path",
        env.EnvOrDefaultStr(
            "PROCESSION_CERT_PATH", defaultCertPath,
        ),
        "Path to the TLS cert file",
    )
    optKeyPath := flag.String(
        "key-path",
        env.EnvOrDefaultStr(
            "PROCESSION_KEY_PATH", defaultKeyPath,
        ),
        "Path to the TLS key file",
    )
    optPort := flag.Int(
        "port",
        env.EnvOrDefaultInt(
            "PROCESSION_PORT", defaultPort,
        ),
        "The server port",
    )

    cfg.ParseCliOpts()

    return &Config{
        UseTLS: *optUseTLS,
        CertPath: *optCertPath,
        KeyPath: *optKeyPath,
        Port: *optPort,
    }
}
