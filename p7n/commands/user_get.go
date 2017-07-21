package commands

import (
    "fmt"
    "os"

    "golang.org/x/net/context"

    "github.com/spf13/cobra"
    pb "github.com/jaypipes/procession/proto"
)

var userGetCommand = &cobra.Command{
    Use: "get <search>",
    Short: "Get information for a single user",
    Run: userGet,
}

func userGet(cmd *cobra.Command, args []string) {
    checkAuthUser(cmd)
    if len(args) == 0 {
        fmt.Println("Please specify an email, UUID, name or slug to search for.")
        cmd.Usage()
        os.Exit(1)
    }
    conn := connect()
    defer conn.Close()

    client := pb.NewIAMClient(conn)
    req := &pb.UserGetRequest{
        Session: &pb.Session{User: authUser},
        Search: args[0],
    }
    user, err := client.UserGet(context.Background(), req)
    exitIfError(err)
    fmt.Printf("UUID:         %s\n", user.Uuid)
    fmt.Printf("Display name: %s\n", user.DisplayName)
    fmt.Printf("Email:        %s\n", user.Email)
    fmt.Printf("Slug:         %s\n", user.Slug)
}
