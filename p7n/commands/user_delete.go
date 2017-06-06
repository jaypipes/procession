package commands

import (
    "fmt"
    "golang.org/x/net/context"

    "github.com/spf13/cobra"
    pb "github.com/jaypipes/procession/proto"
)

var userDeleteCommand = &cobra.Command{
    Use: "delete <user>",
    Short: "Deletes a user and all of its resources",
    RunE: userDelete,
}

func userDelete(cmd *cobra.Command, args []string) error {
    checkAuthUser(cmd)
    if len(args) != 1 {
        fmt.Println("Please specify a user identifier.")
        cmd.Usage()
        return nil
    }
    conn := connect()
    defer conn.Close()

    userId := args[0]
    client := pb.NewIAMClient(conn)
    req := &pb.UserDeleteRequest{
        Session: &pb.Session{User: authUser},
        Search: userId,
    }

    _, err := client.UserDelete(context.Background(), req)
    if err != nil {
        return err
    }
    fmt.Printf("Successfully deleted user %s\n", userId)
    return nil
}
