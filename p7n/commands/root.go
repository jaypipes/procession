package commands

import (
    "fmt"

    "google.golang.org/grpc"
    "github.com/spf13/cobra"

    "github.com/jaypipes/procession/pkg/env"
)

const (
    unsetSentinel = "<not set>"

    defaultConnectHost = "localhost"
    defaultConnectPort = 10000
)

var (
    verbose bool
    connectHost string
    connectPort int
    authUser string
)

var RootCommand = &cobra.Command{
    Use: "p7n",
    Short: "p7n - the Procession CLI tool.",
    Long: "Manipulate a Procession code review system.",
}

func addConnectFlags() {
    RootCommand.PersistentFlags().BoolVarP(
        &verbose,
        "verbose", "v",
        false,
        "Show more output.",
    )
    RootCommand.PersistentFlags().StringVarP(
        &connectHost,
        "host", "",
        env.EnvOrDefaultStr(
            "PROCESSION_HOST",
            defaultConnectHost,
        ),
        "The host where the Procession API can be found.",
    )
    RootCommand.PersistentFlags().IntVarP(
        &connectPort,
        "port", "",
        env.EnvOrDefaultInt(
            "PROCESSION_PORT",
            defaultConnectPort,
        ),
        "The port where the Procession API can be found.",
    )
    RootCommand.PersistentFlags().StringVarP(
        &authUser,
        "user", "",
        env.EnvOrDefaultStr(
            "PROCESSION_USER",
            unsetSentinel,
        ),
        "UUID, email or \"slug\" of the user to log in to Procession with.",
    )
}

func init() {
    addConnectFlags()

    RootCommand.AddCommand(userCommand)
    RootCommand.AddCommand(orgCommand)
    RootCommand.AddCommand(meCommand)
    RootCommand.AddCommand(helpEnvCommand)
    RootCommand.SilenceUsage = true
}

func connect() (*grpc.ClientConn, error) {
    var opts []grpc.DialOption
    opts = append(opts, grpc.WithInsecure())
    connectAddress := fmt.Sprintf("%s:%d", connectHost, connectPort)
    conn, err := grpc.Dial(connectAddress, opts...)
    if err != nil {
        return nil, err
    }
    return conn, nil
}

func isSet(opt string) bool {
    return opt != unsetSentinel
}

func printIf(b bool, msg string, args ...interface{}) {
    if b {
        fmt.Printf(msg, args...)
    }
}
