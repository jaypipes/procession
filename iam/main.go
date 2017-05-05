package main

import (
    "fmt"
    "log"
    "net"
    "path/filepath"

    "google.golang.org/grpc"

    "google.golang.org/grpc/credentials"

    flag "github.com/ogier/pflag"
    "github.com/jaypipes/gsr"

    pb "github.com/jaypipes/procession/proto"

    "github.com/jaypipes/procession/pkg/cfg"
    "github.com/jaypipes/procession/pkg/env"

    "github.com/jaypipes/procession/pkg/iam/rpc"
    "github.com/jaypipes/procession/pkg/iam/iamdb"
)

const (
    cfgPath = "/etc/procession/iam"
    defaultUseTls = false
    defaultPort = 10000
)

var (
    registry *gsr.Registry
    defaultCertPath = filepath.Join(cfgPath, "server.pem")
    defaultKeyPath = filepath.Join(cfgPath, "server.key")
    optUseTls = flag.Bool(
        "tls",
        env.EnvOrDefaultBool(
            "PROCESSION_USE_TLS", defaultUseTls,
        ),
        "Connection uses TLS if true, else plain TCP",
    )
    optCertPath = flag.String(
        "cert-path",
        env.EnvOrDefaultStr(
            "PROCESSION_CERT_PATH", defaultCertPath,
        ),
        "Path to the TLS cert file",
    )
    optKeyPath = flag.String(
        "key-path",
        env.EnvOrDefaultStr(
            "PROCESSION_KEY_PATH", defaultKeyPath,
        ),
        "Path to the TLS key file",
    )
    optPort = flag.Int(
        "port",
        env.EnvOrDefaultInt(
            "PROCESSION_PORT", defaultPort,
        ),
        "The server port",
    )
)

func main() {
    var err error
    var opts []grpc.ServerOption
    srv := rpc.Server{}

    registry, err = gsr.NewRegistry()
    if err != nil {
        log.Fatalf("failed to create gsr.Registry object: %v", err)
    }
    info("connected to gsr service registry.")

    srv.Db, err = iamdb.NewDB()
    if err != nil {
        log.Fatalf("failed to ping iam database: %v", err)
    }
    defer srv.Db.Close()
    info("connected to DB.")

    cfg.ParseCliOpts()
    if *optUseTls {
        creds, err := credentials.NewServerTLSFromFile(
            *optCertPath,
            *optKeyPath,
        )
        if  err != nil {
            log.Fatalf("failed to generate credentials: %v", err)
        }
        opts = []grpc.ServerOption{grpc.Creds(creds)}
        debug("using credentials file %v", *optKeyPath)
    }
    lis, err := net.Listen("tcp", fmt.Sprintf(":%d", *optPort))
    if err != nil {
        log.Fatalf("failed to listen: %v", err)
    }
    info("listening on TCP port %v", *optPort)
    grpcServer := grpc.NewServer(opts...)
    pb.RegisterIAMServer(grpcServer, &srv)
    grpcServer.Serve(lis)
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
