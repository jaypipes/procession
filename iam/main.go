package main

import (
    "fmt"
    "net"
    "os"

    "google.golang.org/grpc"
    "google.golang.org/grpc/credentials"

    pb "github.com/jaypipes/procession/proto"

    "github.com/jaypipes/procession/pkg/context"

    "github.com/jaypipes/procession/pkg/iam/server"
)

func main() {
    ctx := context.New()
    defer ctx.Close()
    reset := ctx.LogSection("iam")
    defer reset()

    srv, err := server.New(ctx)
    if err != nil {
        ctx.LERR("Failed to create IAM server: %v", err)
        os.Exit(1)
    }

    cfg := srv.Config

    var opts []grpc.ServerOption
    if cfg.UseTLS {
        creds, err := credentials.NewServerTLSFromFile(
            cfg.CertPath,
            cfg.KeyPath,
        )
        if err != nil {
            ctx.LERR("failed to generate credentials: %v", err)
            os.Exit(1)
        }
        opts = []grpc.ServerOption{grpc.Creds(creds)}
        ctx.L2("using credentials file %v", cfg.KeyPath)
    }
    lis, err := net.Listen("tcp", fmt.Sprintf(":%d", cfg.Port))
    if err != nil {
        ctx.LERR("failed to listen: %v", err)
        os.Exit(1)
    }
    ctx.L2("listening on TCP port %v", cfg.Port)
    grpcServer := grpc.NewServer(opts...)
    pb.RegisterIAMServer(grpcServer, srv)
    grpcServer.Serve(lis)
}
