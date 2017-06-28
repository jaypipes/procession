package commands

import (
    "fmt"
    "os"
    "golang.org/x/net/context"

    "github.com/spf13/cobra"
    pb "github.com/jaypipes/procession/proto"
)

var (
    roleUpdateDisplayName string
    roleUpdateOrganizationUuid string
)

var roleUpdateCommand = &cobra.Command{
    Use: "update <identifier>",
    Short: "Updates information for an role",
    RunE: roleUpdate,
}

func setupRoleUpdateFlags() {
    roleUpdateCommand.Flags().StringVarP(
        &roleUpdateDisplayName,
        "display-name", "n",
        "",
        "Display name for the role.",
    )
    roleUpdateCommand.Flags().StringVarP(
        &roleUpdateOrganizationUuid,
        "organization-uuid", "o",
        "",
        "UUID of the organization the role should be scoped to, if any.",
    )
}

func init() {
    setupRoleUpdateFlags()
}

func roleUpdate(cmd *cobra.Command, args []string) error {
    checkAuthUser(cmd)
    conn := connect()
    defer conn.Close()

    client := pb.NewIAMClient(conn)
    req := &pb.RoleSetRequest{
        Session: &pb.Session{User: authUser},
        Changed: &pb.RoleSetFields{},
    }

    if len(args) != 1 {
        fmt.Println("Please specify an role identifier.")
        cmd.Usage()
        os.Exit(1)
    } else {
        req.Search = &pb.StringValue{Value: args[0]}
    }

    if cmd.Flags().Changed("display-name") {
        req.Changed.DisplayName = &pb.StringValue{
            Value: roleUpdateDisplayName,
        }
    }
    if cmd.Flags().Changed("organization-uuid") {
        req.Changed.OrganizationUuid = &pb.StringValue{
            Value: roleUpdateOrganizationUuid,
        }
    }
    resp, err := client.RoleSet(context.Background(), req)
    if err != nil {
        return err
    }
    if ! quiet {
        role := resp.Role
        fmt.Printf("Successfully saved role %s\n", role.Uuid)
        fmt.Printf("UUID:         %s\n", role.Uuid)
        if role.OrganizationUuid != nil {
            fmt.Printf("Organization:       %s\n", role.OrganizationUuid.Value)
        }
        fmt.Printf("Display name: %s\n", role.DisplayName)
        fmt.Printf("Slug:         %s\n", role.Slug)
    }
    return nil
}

