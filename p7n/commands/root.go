package commands

import (
    "fmt"
    "io/ioutil"
    "log"
    "os"

    "google.golang.org/grpc"
    "google.golang.org/grpc/grpclog"
    "github.com/spf13/cobra"

    "github.com/jaypipes/procession/pkg/env"
)

type Logger grpclog.Logger

const (
    errUnsetUser = `Error: unable to find the authenticating user.

Please set the PROCESSION_USER environment variable or supply a value
for the --user CLI option.
`
    errConnect = `Error: unable to connect to the Procession server.

Please check the PROCESSION_HOST and PROCESSION_PORT environment
variables or --host and --port  CLI options.
`
)

const (
    defaultConnectHost = "localhost"
    defaultConnectPort = 10000
)

var (
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
    RootCommand.AddCommand(meCommand)
    RootCommand.AddCommand(helpEnvCommand)
    RootCommand.SilenceUsage = true

    clientLog = log.New(ioutil.Discard, "", 0)
    grpclog.SetLogger(clientLog)
}

func connect() (*grpc.ClientConn) {
    var opts []grpc.DialOption
    opts = append(opts, grpc.WithInsecure())
    connectAddress := fmt.Sprintf("%s:%d", connectHost, connectPort)
    conn, err := grpc.Dial(connectAddress, opts...)
    if err != nil {
        fmt.Println(errConnect)
        os.Exit(1)
        return nil
    }
    return conn
}

func exitIfConnectErr(err error) {
    if err != nil {
        fmt.Println(errConnect)
        os.Exit(1)
    }
}

func checkAuthUser(cmd *cobra.Command) {
    if authUser == "" && ! cmd.Flags().Changed("user") {
        fmt.Println(errUnsetUser)
        cmd.Usage()
        os.Exit(1)
    }
}

func printIf(b bool, msg string, args ...interface{}) {
    if b {
        fmt.Printf(msg, args...)
    }
}
