package commands

import (
    "fmt"
    "os"
    "strings"

    "github.com/spf13/cobra"
    "google.golang.org/grpc"
    "google.golang.org/grpc/codes"
    "google.golang.org/grpc/status"

    pb "github.com/jaypipes/procession/proto"
)

const (
    permissionsHelpExtended = `

    NOTE: To find out what permissions may be applied to a role, use
          the p7n permissions command.
`
)

const (
    rolesHelpExtended = `

    NOTE: To find out what roles a user may be added to, use
          the p7n role list command.
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
    errBadVisibility = `Error: incorrect value for visibility.

Valid values are PUBLIC or PRIVATE.
`
)

const (
    msgNoRecords = "No records found matching search criteria."
)

// Some commonly-used CLI options
const (
    defaultListLimit = 20
)

var (
    listLimit int
    listMarker string
)

// Checks the given string to ensure it matches an appropriate value for a
// visibility setting and returns the matching integer value or exits with a
// usage message
func checkVisibility(cmd *cobra.Command, value string) pb.Visibility {
    ival, found := pb.Visibility_value[strings.ToUpper(value)]
    if ! found {
        fmt.Println(errBadVisibility)
        cmd.Usage()
        os.Exit(1)
    }
    return pb.Visibility(ival)
}

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
            fmt.Printf("Error: %s\n", s.Message())
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

// Appends the standard listing CLI options to the supplied command struct
func addListOptions(cmd *cobra.Command) {
    cmd.Flags().IntVarP(
        &listLimit,
        "limit", "",
        defaultListLimit,
        "Number of records to limit results to.",
    )
    cmd.Flags().StringVarP(
        &listMarker,
        "marker", "",
        "",
        "Identifier of the last record on the previous page of results.",
    )
}

// Examines the supplied search listing options and returns a constructed
// pb.SearchOptions message struct for use in the request to the Procession
// service
func buildSearchOptions(cmd *cobra.Command) *pb.SearchOptions {
    res := &pb.SearchOptions{
        Limit: uint32(listLimit),
        Marker: listMarker,
    }
    return res
}
