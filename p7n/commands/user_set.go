package commands

import (
    "fmt"
    "golang.org/x/net/context"

    "github.com/spf13/cobra"
    pb "github.com/jaypipes/procession/proto"
)

var (
    userSetDisplayName string
    userSetEmail string
)

var userSetCommand = &cobra.Command{
    Use: "set [<uuid>]",
    Short: "Creates/updates information for a user",
    RunE: userSet,
}

func setupUserSetFlags() {
    userSetCommand.Flags().StringVarP(
        &userSetDisplayName,
        "display-name", "n",
        unsetSentinel,
        "Display name for the user.",
    )
    userSetCommand.Flags().StringVarP(
        &userSetEmail,
        "email", "e",
        unsetSentinel,
        "Email for the user.",
    )
}

func init() {
    setupUserSetFlags()
}

func userSet(cmd *cobra.Command, args []string) error {
    newUser := true
    conn, err := connect()
    if err != nil {
        return err
    }
    defer conn.Close()

    client := pb.NewIAMClient(conn)
    req := &pb.UserSetRequest{
        Session: nil,
        Changed: &pb.UserSetFields{},
    }

    if len(args) == 1 {
        newUser = false
        req.Search = &pb.StringValue{Value: args[0]}
    }

    if isSet(userSetDisplayName) {
        req.Changed.DisplayName = &pb.StringValue{
            Value: userSetDisplayName,
        }
    }
    if isSet(userSetEmail) {
        req.Changed.Email = &pb.StringValue{
            Value: userSetEmail,
        }
    }
    resp, err := client.UserSet(context.Background(), req)
    if err != nil {
        return err
    }
    user := resp.User
    if newUser {
        fmt.Printf("Successfully created user with UUID %s\n", user.Uuid)
    } else {
        fmt.Printf("Successfully saved user <%s>\n", user.Uuid)
    }
    fmt.Printf("UUID:         %s\n", user.Uuid)
    fmt.Printf("Display name: %s\n", user.DisplayName)
    fmt.Printf("Email:        %s\n", user.Email)
    fmt.Printf("Slug:         %s\n", user.Slug)
    return nil
}
