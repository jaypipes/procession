package commands

import (
    "fmt"
    "golang.org/x/net/context"

    "github.com/spf13/cobra"
    pb "github.com/jaypipes/procession/proto"
)

var orgGetCommand = &cobra.Command{
    Use: "get <search>",
    Short: "Get information for a single organization",
    RunE: orgGet,
}

func orgGet(cmd *cobra.Command, args []string) error {
    checkAuthUser(cmd)
    if len(args) == 0 {
        fmt.Println("Please specify a UUID, name or slug to search for.")
        cmd.Usage()
        return nil
    }
    conn := connect()
    defer conn.Close()

    client := pb.NewIAMClient(conn)
    req := &pb.OrganizationGetRequest{
        Session: &pb.Session{User: authUser},
        Search: args[0],
    }
    org, err := client.OrganizationGet(context.Background(), req)
    exitIfError(err)
    if org.Uuid == "" {
        fmt.Printf("No organization found matching request\n")
        return nil
    }
    fmt.Printf("UUID:         %s\n", org.Uuid)
    fmt.Printf("Display name: %s\n", org.DisplayName)
    fmt.Printf("Slug:         %s\n", org.Slug)
    if org.Parent != nil {
        fmt.Printf(
            "Parent:       %s [%s]\n",
            org.Parent.DisplayName,
            org.Parent.Uuid,
        )
    }
    return nil
}
