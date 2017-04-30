package commands

import (
    "fmt"
    "golang.org/x/net/context"

    "github.com/spf13/cobra"
    pb "github.com/jaypipes/procession/proto"
)

var userShowCommand = &cobra.Command{
    Use: "show <uuid>",
    Short: "Show information for a user",
    RunE: showUser,
}

func showUser(cmd *cobra.Command, args []string) error {
    if len(args) != 1 {
        fmt.Println("Please specify an email, user UUID, or display name")
        cmd.Usage()
        return nil
    }
    conn, err := connect()
    if err != nil {
        return err
    }
    defer conn.Close()

    uuid := args[0]
    client := pb.NewIAMClient(conn)
    req := &pb.GetUserRequest{
        Session: nil,
        UserUuid: uuid,
    }
    user, err := client.GetUser(context.Background(), req)
    if err != nil {
        return err
    }
    if user.Uuid == "" {
        fmt.Printf("No user found matching UUID %s\n", uuid)
        return nil
    }
    fmt.Printf("UUID:         %s\n", user.Uuid)
    fmt.Printf("Display name: %s\n", user.DisplayName)
    fmt.Printf("Email:        %s\n", user.Email)
    return nil
}
