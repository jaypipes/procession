package main

import (
    "fmt"
    "net"
    "os"

    "google.golang.org/grpc"
    "google.golang.org/grpc/credentials"
    "github.com/jaypipes/gsr"

    pb "github.com/jaypipes/procession/proto"

    "github.com/jaypipes/procession/pkg/logging"
    "github.com/jaypipes/procession/pkg/iam/server"
)

const (
    SERVICE_NAME = "procession-iam"
)

func main() {
    log := logging.New(logging.ConfigFromOpts())

    defer log.WithSection("iam")()

    srvcfg := server.ConfigFromOpts()

    srv, err := server.New(srvcfg, log)
    if err != nil {
        log.ERR("Failed to create IAM server: %v", err)
        os.Exit(1)
    }
    defer srv.Close()

    addr := fmt.Sprintf("%s:%d", srvcfg.BindHost, srvcfg.BindPort)
    lis, err := net.Listen("tcp", addr)
    if err != nil {
        log.ERR("failed to listen: %v", err)
        os.Exit(1)
    }
    log.L2("listening on TCP %s", addr)

    // Register this IAM service endpoint with the service registry
    ep := gsr.Endpoint{
        Service: &gsr.Service{SERVICE_NAME},
        Address: addr,
    }
    err = srv.Registry.Register(&ep)
    if err != nil {
        log.ERR("unable to register %v with gsr: %v", ep, err)
    }
    log.L2(
        "Registered IAM service endpoint running at %s with gsr.",
        addr,
    )

    // Set up the gRPC server listening on incoming TCP connections on our port
    var opts []grpc.ServerOption
    if srvcfg.UseTLS {
        creds, err := credentials.NewServerTLSFromFile(
            srvcfg.CertPath,
            srvcfg.KeyPath,
        )
        if err != nil {
            log.ERR("failed to generate credentials: %v", err)
            os.Exit(1)
        }
        opts = []grpc.ServerOption{grpc.Creds(creds)}
        log.L2("using credentials file %v", srvcfg.KeyPath)
    }
    grpcServer := grpc.NewServer(opts...)
    pb.RegisterIAMServer(grpcServer, srv)
    grpcServer.Serve(lis)
}
