package commands

import (
    "fmt"
    "golang.org/x/net/context"

    "github.com/spf13/cobra"
    pb "github.com/jaypipes/procession/proto"
)

var (
    displayName string
    email string
)

var userSetCommand = &cobra.Command{
    Use: "set [<uuid>]",
    Short: "Creates/updates information for a user",
    RunE: setUser,
}

func addUserSetFlags() {
    userSetCommand.Flags().StringVarP(
        &displayName,
        "display-name", "n",
        "",
        "Display name for the user.",
    )
    userSetCommand.Flags().StringVarP(
        &email,
        "email", "e",
        "",
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
        User: &pb.User{
            Uuid: uuid,
            Email: email,
            DisplayName: displayName,
        },
    }
    _, err = client.SetUser(context.Background(), req)
    if err != nil {
        return err
    }
    if newUser {
        fmt.Printf("Successfully created user\n")
        return nil
    } else {
        fmt.Printf("Successfully saved user <%s>\n", uuid)
        return nil
    }
}

