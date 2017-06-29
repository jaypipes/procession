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
    roleUpdateDisplayName string
    roleUpdateOrganization string
    roleUpdateAddPermissions string
    roleUpdateRemovePermissions string
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
        &roleUpdateOrganization,
        "organization", "o",
        "",
        "UUID of the organization the role should be scoped to, if any.",
    )
    roleUpdateCommand.Flags().StringVarP(
        &roleUpdateAddPermissions,
        "add", "",
        "",
        "Comma-separated list of permission strings to add to this role." +
        permissionsHelpExtended,
    )
    roleUpdateCommand.Flags().StringVarP(
        &roleUpdateRemovePermissions,
        "remove", "",
        "",
        "Comma-separated list of permission strings to remove from this " +
        "role." + permissionsHelpExtended,
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
    if cmd.Flags().Changed("organization") {
        req.Changed.Organization = &pb.StringValue{
            Value: roleUpdateOrganization,
        }
    }
    if cmd.Flags().Changed("add") {
        permStrings := strings.Split(roleUpdateAddPermissions, ",")
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
    if cmd.Flags().Changed("remove") {
        permStrings := strings.Split(roleUpdateRemovePermissions, ",")
        permsToRemove := make([]pb.Permission, len(permStrings))
        for x, permStr := range permStrings {
            permStr = strings.TrimSpace(permStr)
            if perm, found := pb.Permission_value[permStr]; found {
                permsToRemove[x] = pb.Permission(perm)
            } else {
                fmt.Printf("Unknown permission %s\n", permStr)
                os.Exit(1)
            }
        }
        req.Changed.Remove = &pb.PermissionSet{
            Permissions: permsToRemove,
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
        if role.Organization != nil {
            fmt.Printf("Organization:       %s\n", role.Organization.Value)
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

