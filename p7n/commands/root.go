package commands

import (
    "google.golang.org/grpc"
    "github.com/spf13/cobra"

    "github.com/jaypipes/procession/pkg/env"
)

var (
    verbose bool
    apiAddress string

    defaultApiAddress string = "localhost"
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
        &apiAddress,
        "api-address", "s",
        env.EnvOrDefaultStr(
            "PROCESSION_API_ADDRESS",
            defaultApiAddress,
        ),
        "Address of the Procession API server to connect to.",
    )
}

func init() {
    addConnectFlags()

    RootCommand.AddCommand(userCommand)
    RootCommand.AddCommand(helpEnvCommand)
    RootCommand.SilenceUsage = true
}

func connect() (*grpc.ClientConn, error) {
    var opts []grpc.DialOption
    opts = append(opts, grpc.WithInsecure())
    conn, err := grpc.Dial(apiAddress, opts...)
    if err != nil {
        return nil, err
    }
    return conn, nil
}
