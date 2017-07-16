package server

import (
    "path/filepath"

    flag "github.com/ogier/pflag"

    "github.com/jaypipes/procession/pkg/env"
    "github.com/jaypipes/procession/pkg/util"
)

const (
    cfgPath = "/etc/procession/iam"
    defaultUseTLS = false
    defaultBindPort = 10000
    defaultDSN = "user:password@/dbname"
    defaultServiceName = "procession-iam"
)

var (
    defaultCertPath = filepath.Join(cfgPath, "server.pem")
    defaultKeyPath = filepath.Join(cfgPath, "server.key")
    defaultBindHost = util.BindHost()
)

type Config struct {
    DSN string
    UseTLS bool
    CertPath string
    KeyPath string
    BindHost string
    BindPort int
    ServiceName string
}

func ConfigFromOpts() *Config {
    optDSN := flag.String(
        "dsn",
        env.EnvOrDefaultStr(
            "PROCESSION_DSN", defaultDSN,
        ),
        "Data Source Name (DSN) for connecting to the IAM data store",
    )
    optUseTLS := flag.Bool(
        "use-tls",
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
    optHost := flag.String(
        "bind-address",
        env.EnvOrDefaultStr(
            "PROCESSION_BIND_HOST", defaultBindHost,
        ),
        "The host address the server will listen on",
    )
    optPort := flag.Int(
        "bind-port",
        env.EnvOrDefaultInt(
            "PROCESSION_BIND_PORT", defaultBindPort,
        ),
        "The port the server will listen on",
    )
    optServiceName := flag.String(
        "service-name",
        env.EnvOrDefaultStr(
            "PROCESSION_SERVICE_NAME", defaultServiceName,
        ),
        "Name of the service to register",
    )

    flag.Parse()

    return &Config{
        DSN: *optDSN,
        UseTLS: *optUseTLS,
        CertPath: *optCertPath,
        KeyPath: *optKeyPath,
        BindHost: *optHost,
        BindPort: *optPort,
        ServiceName: *optServiceName,
    }
}
