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
    "github.com/jaypipes/procession/pkg/context"
    "github.com/jaypipes/procession/pkg/env"

    "github.com/jaypipes/procession/pkg/iam/db"
    "github.com/jaypipes/procession/pkg/iam/rpc"
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

    ctx := context.New()
    reset := ctx.LogSection("iam")
    defer reset()

    var opts []grpc.ServerOption
    srv := rpc.Server{}

    registry, err = gsr.New()
    if err != nil {
        log.Fatalf("failed to create gsr.Registry object: %v", err)
    }
    ctx.L2("connected to gsr service registry.")

    db, err := db.New(ctx)
    if err != nil {
        log.Fatalf("failed to ping iam database: %v", err)
    }
    ctx.Db = db
    defer ctx.Close()
    ctx.L2("connected to DB.")

    srv.Ctx = ctx

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
        ctx.L2("using credentials file %v", *optKeyPath)
    }
    lis, err := net.Listen("tcp", fmt.Sprintf(":%d", *optPort))
    if err != nil {
        log.Fatalf("failed to listen: %v", err)
    }
    ctx.L2("listening on TCP port %v", *optPort)
    grpcServer := grpc.NewServer(opts...)
    pb.RegisterIAMServer(grpcServer, &srv)
    grpcServer.Serve(lis)
}
