package commands

import (
    "fmt"

    "google.golang.org/grpc"
    "github.com/spf13/cobra"

    "github.com/jaypipes/procession/pkg/env"
)

const (
    unsetSentinel = "<<UNSET>>"

    defaultApiHost = "localhost"
    defaultApiPort = 10000
)

var (
    verbose bool
    apiHost string
    apiPort int
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
        &apiHost,
        "api-host", "",
        env.EnvOrDefaultStr(
            "PROCESSION_API_HOST",
            defaultApiHost,
        ),
        "The host where the Procession API can be found.",
    )
    RootCommand.PersistentFlags().IntVarP(
        &apiPort,
        "api-port", "",
        env.EnvOrDefaultInt(
            "PROCESSION_API_PORT",
            defaultApiPort,
        ),
        "The port where the Procession API can be found.",
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
    apiAddress := fmt.Sprintf("%s:%d", apiHost, apiPort)
    conn, err := grpc.Dial(apiAddress, opts...)
    if err != nil {
        return nil, err
    }
    return conn, nil
}

func isSet(opt string) bool {
    return opt != unsetSentinel
}
