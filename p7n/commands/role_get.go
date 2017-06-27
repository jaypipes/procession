package commands

import (
    "fmt"
    "strings"
    "golang.org/x/net/context"

    "github.com/spf13/cobra"
    pb "github.com/jaypipes/procession/proto"
)

var roleGetCommand = &cobra.Command{
    Use: "get <search>",
    Short: "Get information for a single role",
    RunE: roleGet,
}

func roleGet(cmd *cobra.Command, args []string) error {
    checkAuthUser(cmd)
    if len(args) == 0 {
        fmt.Println("Please specify a UUID, name or slug to search for.")
        cmd.Usage()
        return nil
    }
    conn := connect()
    defer conn.Close()

    client := pb.NewIAMClient(conn)
    req := &pb.RoleGetRequest{
        Session: &pb.Session{User: authUser},
        Search: args[0],
    }
    role, err := client.RoleGet(context.Background(), req)
    if err != nil {
        return err
    }
    if role.Uuid == "" {
        fmt.Printf("No role found matching request\n")
        return nil
    }
    fmt.Printf("UUID:         %s\n", role.Uuid)
    if role.OrganizationUuid != nil {
        orgUuid := role.OrganizationUuid.Value
        fmt.Printf("Organization: %s\n", orgUuid)
    }
    fmt.Printf("Display name: %s\n", role.DisplayName)
    fmt.Printf("Slug:         %s\n", role.Slug)
    if len(role.Permissions) > 0 {
        strPerms := make([]string, len(role.Permissions))
        for x, perm := range role.Permissions {
            strPerms[x] = perm.String()
        }
        permStr := strings.Join(strPerms, ", ")
        fmt.Printf("Permissions:  %s\n", permStr)
    } else {
        fmt.Printf("Permissions:  None\n")
    }
    return nil
}
