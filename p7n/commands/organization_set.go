package commands

import (
    "fmt"
    "golang.org/x/net/context"

    "github.com/spf13/cobra"
    pb "github.com/jaypipes/procession/proto"
)

var (
    setOrganizationDisplayName string
    setOrganizationParentUuid string
)

var organizationSetCommand = &cobra.Command{
    Use: "set [<uuid>]",
    Short: "Creates/updates information for a organization",
    RunE: setOrganization,
}

func addOrganizationSetFlags() {
    organizationSetCommand.Flags().StringVarP(
        &setOrganizationDisplayName,
        "display-name", "n",
        unsetSentinel,
        "Display name for the organization.",
    )
    organizationSetCommand.Flags().StringVarP(
        &setOrganizationParentUuid,
        "parent-uuid", "",
        unsetSentinel,
        "UUID of the parent organization, if any.",
    )
}

func init() {
    addOrganizationSetFlags()
}

func setOrganization(cmd *cobra.Command, args []string) error {
    newOrganization := true
    conn, err := connect()
    if err != nil {
        return err
    }
    defer conn.Close()

    client := pb.NewIAMClient(conn)
    req := &pb.SetOrganizationRequest{
        Session: nil,
        OrganizationFields: &pb.SetOrganizationFields{},
    }

    if len(args) == 1 {
        newOrganization = false
        req.Search = &pb.StringValue{Value: args[0]}
    }

    if isSet(setOrganizationDisplayName) {
        req.OrganizationFields.DisplayName = &pb.StringValue{
            Value: setOrganizationDisplayName,
        }
    }
    if isSet(setOrganizationParentUuid) {
        req.OrganizationFields.ParentOrganizationUuid = &pb.StringValue{
            Value: setOrganizationParentUuid,
        }
    }
    resp, err := client.SetOrganization(context.Background(), req)
    if err != nil {
        return err
    }
    organization := resp.Organization
    if newOrganization {
        fmt.Printf("Successfully created organization with UUID %s\n", organization.Uuid)
    } else {
        fmt.Printf("Successfully saved organization <%s>\n", organization.Uuid)
    }
    fmt.Printf("UUID:         %s\n", organization.Uuid)
    fmt.Printf("Display name: %s\n", organization.DisplayName)
    fmt.Printf("Slug:         %s\n", organization.Slug)
    return nil
}
