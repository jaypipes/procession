package commands

import (
    "fmt"
    "golang.org/x/net/context"

    "github.com/spf13/cobra"
    pb "github.com/jaypipes/procession/proto"
)

var (
    orgSetDisplayName string
    orgSetParentUuid string
)

var orgSetCommand = &cobra.Command{
    Use: "set [<uuid>]",
    Short: "Creates/updates information for an organization",
    RunE: orgSet,
}

func setupOrgSetFlags() {
    orgSetCommand.Flags().StringVarP(
        &orgSetDisplayName,
        "display-name", "n",
        "",
        "Display name for the organization.",
    )
    orgSetCommand.Flags().StringVarP(
        &orgSetParentUuid,
        "parent-uuid", "",
        "",
        "UUID of the parent organization, if any.",
    )
}

func init() {
    setupOrgSetFlags()
}

func orgSet(cmd *cobra.Command, args []string) error {
    checkAuthUser(cmd)
    newOrganization := true
    conn := connect()
    defer conn.Close()

    client := pb.NewIAMClient(conn)
    req := &pb.OrganizationSetRequest{
        Session: &pb.Session{User: authUser},
        Changed: &pb.OrganizationSetFields{},
    }

    if len(args) == 1 {
        newOrganization = false
        req.Search = &pb.StringValue{Value: args[0]}
    }

    if cmd.Flags().Changed("display-name") {
        req.Changed.DisplayName = &pb.StringValue{
            Value: orgSetDisplayName,
        }
    }
    if cmd.Flags().Changed("parent-uuid") {
        req.Changed.ParentUuid = &pb.StringValue{
            Value: orgSetParentUuid,
        }
    }
    resp, err := client.OrganizationSet(context.Background(), req)
    if err != nil {
        return err
    }
    org := resp.Organization
    if newOrganization {
        fmt.Printf("Successfully created organization with UUID %s\n", org.Uuid)
    } else {
        fmt.Printf("Successfully saved organation %s\n", org.Uuid)
    }
    fmt.Printf("UUID:         %s\n", org.Uuid)
    fmt.Printf("Display name: %s\n", org.DisplayName)
    fmt.Printf("Slug:         %s\n", org.Slug)
    if org.ParentUuid != nil {
        fmt.Printf("Parent:       %s\n", org.ParentUuid.Value)
    }
    return nil
}
