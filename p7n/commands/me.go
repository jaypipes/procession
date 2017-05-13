package commands

import (
    "fmt"
    "golang.org/x/net/context"

    "github.com/spf13/cobra"
    pb "github.com/jaypipes/procession/proto"
)

const (
    errUnsetUser = `Error: unable to find the authenticating user.

Please set the PROCESSION_USER environment variable or supply a value
for the --user CLI option.
`
)

var meCommand = &cobra.Command{
    Use: "me",
    Short: "Shows information about the context that will be used to execute a command",
    RunE: runMe,
}

func init() {
}

func runMe(cmd *cobra.Command, args []string) error {
    if ! isSet(authUser) {
        fmt.Println(errUnsetUser)
        cmd.Usage()
        return nil
    }
    conn, err := connect()
    if err != nil {
        return err
    }
    defer conn.Close()

    client := pb.NewIAMClient(conn)
    req := &pb.GetUserRequest{
        Session: nil,
        Search: authUser,
    }
    user, err := client.GetUser(context.Background(), req)
    if err != nil {
        return err
    }
    if user.Uuid == "" {
        fmt.Println("Error: unknown or invalid user information.")
        return nil
    }
    fmt.Println("OK")
    return nil
}
