package commands

import (
    "fmt"
    "golang.org/x/net/context"

    "github.com/spf13/cobra"
    pb "github.com/jaypipes/procession/proto"
)

var organizationGetCommand = &cobra.Command{
    Use: "get <search>",
    Short: "Get information for a single organization",
    RunE: getOrganization,
}

func init() {
}

func getOrganization(cmd *cobra.Command, args []string) error {
    if len(args) == 0 {
        fmt.Println("Please specify a UUID, name or slug to search for.")
        cmd.Usage()
        return nil
    }
    conn, err := connect()
    if err != nil {
        return err
    }
    defer conn.Close()

    client := pb.NewIAMClient(conn)
    req := &pb.GetOrganizationRequest{
        Session: nil,
        Search: args[0],
    }
    organization, err := client.GetOrganization(context.Background(), req)
    if err != nil {
        return err
    }
    if organization.Uuid == "" {
        fmt.Printf("No organization found matching request\n")
        return nil
    }
    fmt.Printf("UUID:         %s\n", organization.Uuid)
    fmt.Printf("Display name: %s\n", organization.DisplayName)
    fmt.Printf("Slug:         %s\n", organization.Slug)
    return nil
}

