package commands

import (
    "fmt"
    "os"
    "strings"

    "golang.org/x/net/context"

    "github.com/spf13/cobra"
    pb "github.com/jaypipes/procession/proto"
)

var (
    roleCreateDisplayName string
    roleCreateOrganization string
    roleCreatePermissions string
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
        &roleCreateOrganization,
        "organization", "",
        "",
        "Identifier of an organization the role should be scoped to, if any.",
    )
    roleCreateCommand.Flags().StringVarP(
        &roleCreatePermissions,
        "permissions", "",
        "",
        "Comma-separated list of permission strings to allow for this role." +
        permissionsHelpExtended,
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
    if cmd.Flags().Changed("organization") {
        req.Changed.Organization = &pb.StringValue{
            Value: roleCreateOrganization,
        }
    }
    if cmd.Flags().Changed("permissions") {
        permStrings := strings.Split(roleCreatePermissions, ",")
        permsToAdd := make([]pb.Permission, len(permStrings))
        for x, permStr := range permStrings {
            permStr = strings.TrimSpace(permStr)
            if perm, found := pb.Permission_value[permStr]; found {
                permsToAdd[x] = pb.Permission(perm)
            } else {
                fmt.Printf("Unknown permission %s\n", permStr)
                os.Exit(1)
            }
        }
        req.Changed.Add = &pb.PermissionSet{
            Permissions: permsToAdd,
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
        if role.Organization != nil {
            fmt.Printf(
                "Organization: %s\n",
                role.Organization.DisplayName,
            )
        }
        fmt.Printf("Display name: %s\n", role.DisplayName)
        fmt.Printf("Slug:         %s\n", role.Slug)
        if (role.PermissionSet != nil &&
                len(role.PermissionSet.Permissions) > 0) {
            strPerms := make([]string, len(role.PermissionSet.Permissions))
            for x, perm := range role.PermissionSet.Permissions {
                strPerms[x] = perm.String()
            }
            permStr := strings.Join(strPerms, ", ")
            fmt.Printf("Permissions:  %s\n", permStr)
        } else {
            fmt.Printf("Permissions:  None\n")
        }
    }
    return nil
}

