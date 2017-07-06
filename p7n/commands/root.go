package commands

import (
    "io/ioutil"
    "log"

    "google.golang.org/grpc/grpclog"
    "github.com/spf13/cobra"

    "github.com/jaypipes/procession/pkg/env"
)

type Logger grpclog.Logger

const (
    quietHelpExtended = `

    NOTE: For commands that create, modify or delete an object, the
          --quiet flag triggers the outputting of the newly-created
          object's identifier as the only output from the command.
          For commands that update an object's state, this will quiet
          all output, meaning the user will need to query the result
          code from the p7n program in order to determine success.
`
)

const (
    defaultConnectHost = "localhost"
    defaultConnectPort = 10000
)

var (
    quiet bool
    verbose bool
    connectHost string
    connectPort int
    authUser string
    clientLog Logger
)

var RootCommand = &cobra.Command{
    Use: "p7n",
    Short: "p7n - the Procession CLI tool.",
    Long: "Manipulate a Procession code review system.",
}

func addConnectFlags() {
    RootCommand.PersistentFlags().BoolVarP(
        &quiet,
        "quiet", "q",
        false,
        "Show minimal output." + quietHelpExtended,
    )
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
            "",
        ),
        "UUID, email or \"slug\" of the user to log in to Procession with.",
    )
}

func init() {
    addConnectFlags()

    RootCommand.AddCommand(userCommand)
    RootCommand.AddCommand(orgCommand)
    RootCommand.AddCommand(roleCommand)
    RootCommand.AddCommand(permissionsCommand)
    RootCommand.AddCommand(meCommand)
    RootCommand.AddCommand(helpEnvCommand)
    RootCommand.SilenceUsage = true

    clientLog = log.New(ioutil.Discard, "", 0)
    grpclog.SetLogger(clientLog)
}
