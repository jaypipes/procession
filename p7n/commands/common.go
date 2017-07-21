package commands

import (
    "fmt"
    "os"

    "github.com/spf13/cobra"
    "google.golang.org/grpc"
    "google.golang.org/grpc/codes"
    "google.golang.org/grpc/status"
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
    errForbidden = `Error: you are not authorized to perform that action.`
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

func exitIfForbidden(err error) {
    if s, ok := status.FromError(err); ok {
        if s.Code() == codes.PermissionDenied {
            fmt.Println(errForbidden)
            os.Exit(int(s.Code()))
        }
    }
}

// Writes a generic error to output and exits if supplied error is an error
func exitIfError(err error) {
    if s, ok := status.FromError(err); ok {
        if s.Code() != codes.OK {
            fmt.Println("Error: %s", err)
            os.Exit(int(s.Code()))
        }
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
