package commands

import (
    "fmt"
    "os"

    "github.com/spf13/cobra"
    "google.golang.org/grpc"
)

const (
    permissionsHelpExtended = `

    NOTE: To find out what permissions may be applied to a role, use
          the p7n permissions command.
`
)

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
    msgNoRecords = "No records found matching search criteria."
)

func exitIfConnectErr(err error) {
    if err != nil {
        fmt.Println(errConnect)
        os.Exit(1)
    }
}

func exitNoRecords() {
    if ! quiet {
        fmt.Println(msgNoRecords)
    }
    os.Exit(0)
}

func checkAuthUser(cmd *cobra.Command) {
    if authUser == "" && ! cmd.Flags().Changed("user") {
        fmt.Println(errUnsetUser)
        cmd.Usage()
        os.Exit(1)
    }
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

func printIf(b bool, msg string, args ...interface{}) {
    if b {
        fmt.Printf(msg, args...)
    }
}
