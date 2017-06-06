package commands

import (
    "fmt"
    "golang.org/x/net/context"

    "github.com/spf13/cobra"
    pb "github.com/jaypipes/procession/proto"
)

var orgDeleteCommand = &cobra.Command{
    Use: "delete <organization>",
    Short: "Deletes an organization and all of its resources",
    RunE: orgDelete,
}

func orgDelete(cmd *cobra.Command, args []string) error {
    checkAuthUser(cmd)
    if len(args) != 1 {
        fmt.Println("Please specify an organization identifier.")
        cmd.Usage()
        return nil
    }
    conn := connect()
    defer conn.Close()

    orgId := args[0]
    client := pb.NewIAMClient(conn)
    req := &pb.OrganizationDeleteRequest{
        Session: &pb.Session{User: authUser},
        Search: orgId,
    }

    _, err := client.OrganizationDelete(context.Background(), req)
    if err != nil {
        return err
    }
    fmt.Printf("Successfully deleted organization %s\n", orgId)
    return nil
}
