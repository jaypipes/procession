package commands

import (
    "fmt"
    "os"
    "golang.org/x/net/context"

    "github.com/spf13/cobra"
    pb "github.com/jaypipes/procession/proto"
)

var (
    roleCreateDisplayName string
    roleCreateOrganizationUuid string
)

var roleCreateCommand = &cobra.Command{
    Use: "create",
    Short: "Creates a new role",
    RunE: roleCreate,
}

func setupRoleCreateFlags() {
    roleCreateCommand.Flags().StringVarP(
        &roleCreateDisplayName,
        "display-name", "n",
        "",
        "Display name for the role.",
    )
    roleCreateCommand.Flags().StringVarP(
        &roleCreateOrganizationUuid,
        "organization-uuid", "",
        "",
        "UUID of the organization that the role should be scoped to, if any.",
    )
}

func init() {
    setupRoleCreateFlags()
}

func roleCreate(cmd *cobra.Command, args []string) error {
    checkAuthUser(cmd)
    conn := connect()
    defer conn.Close()

    client := pb.NewIAMClient(conn)
    req := &pb.RoleSetRequest{
        Session: &pb.Session{User: authUser},
        Changed: &pb.RoleSetFields{},
    }

    if cmd.Flags().Changed("display-name") {
        req.Changed.DisplayName = &pb.StringValue{
            Value: roleCreateDisplayName,
        }
    } else {
        fmt.Println("Specify a display name using --display-name=<NAME>.")
        cmd.Usage()
        os.Exit(1)
    }
    if cmd.Flags().Changed("organization-uuid") {
        req.Changed.OrganizationUuid = &pb.StringValue{
            Value: roleCreateOrganizationUuid,
        }
    }
    resp, err := client.RoleSet(context.Background(), req)
    if err != nil {
        return err
    }
    role := resp.Role
    if quiet {
        fmt.Println(role.Uuid)
    } else {
        fmt.Printf("Successfully created role with UUID %s\n", role.Uuid)
        fmt.Printf("UUID:         %s\n", role.Uuid)
        if role.OrganizationUuid != nil {
            fmt.Printf("Organization: %s\n", role.OrganizationUuid.Value)
        }
        fmt.Printf("Display name: %s\n", role.DisplayName)
        fmt.Printf("Slug:         %s\n", role.Slug)
    }
    return nil
}

