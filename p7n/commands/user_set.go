package commands

import (
    "fmt"
    "golang.org/x/net/context"

    "github.com/spf13/cobra"
    pb "github.com/jaypipes/procession/proto"
)

var (
    setUserDisplayName string
    setUserEmail string
)

var userSetCommand = &cobra.Command{
    Use: "set [<uuid>]",
    Short: "Creates/updates information for a user",
    RunE: setUser,
}

func addUserSetFlags() {
    userSetCommand.Flags().StringVarP(
        &setUserDisplayName,
        "display-name", "n",
        unsetSentinel,
        "Display name for the user.",
    )
    userSetCommand.Flags().StringVarP(
        &setUserEmail,
        "email", "e",
        unsetSentinel,
        "Email for the user.",
    )
}

func init() {
    addUserSetFlags()
}

func setUser(cmd *cobra.Command, args []string) error {
    var uuid string
    newUser := true

    if len(args) == 1 {
        newUser = false
        uuid = args[0]
    }
    conn, err := connect()
    if err != nil {
        return err
    }
    defer conn.Close()

    client := pb.NewIAMClient(conn)
    req := &pb.SetUserRequest{
        Session: nil,
        SearchFields: &pb.GetUserFields{
            Uuid: &pb.StringValue{Value: uuid},
        },
        UserFields: &pb.SetUserFields{},
    }

    if isSet(setUserDisplayName) {
        req.UserFields.DisplayName = &pb.StringValue{
            Value: setUserDisplayName,
        }
    }
    if isSet(setUserEmail) {
        req.UserFields.Email = &pb.StringValue{
            Value: setUserEmail,
        }
    }
    resp, err := client.SetUser(context.Background(), req)
    if err != nil {
        return err
    }
    user := resp.User
    if newUser {
        fmt.Printf("Successfully created user with UUID %s\n", user.Uuid)
        return nil
    } else {
        fmt.Printf("Successfully saved user <%s>\n", uuid)
        return nil
    }
}

