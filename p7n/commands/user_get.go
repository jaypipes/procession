package commands

import (
    "fmt"
    "golang.org/x/net/context"

    "github.com/spf13/cobra"
    pb "github.com/jaypipes/procession/proto"
)

var userGetCommand = &cobra.Command{
    Use: "get <search>",
    Short: "Get information for a single user",
    RunE: userGet,
}

func init() {
}

func userGet(cmd *cobra.Command, args []string) error {
    if len(args) == 0 {
        fmt.Println("Please specify an email, UUID, name or slug to search for.")
        cmd.Usage()
        return nil
    }
    conn, err := connect()
    if err != nil {
        return err
    }
    defer conn.Close()

    client := pb.NewIAMClient(conn)
    req := &pb.UserGetRequest{
        Session: nil,
        Search: args[0],
    }
    user, err := client.UserGet(context.Background(), req)
    if err != nil {
        return err
    }
    if user.Uuid == "" {
        fmt.Printf("No user found matching request\n")
        return nil
    }
    fmt.Printf("UUID:         %s\n", user.Uuid)
    fmt.Printf("Display name: %s\n", user.DisplayName)
    fmt.Printf("Email:        %s\n", user.Email)
    fmt.Printf("Slug:         %s\n", user.Slug)
    return nil
}
