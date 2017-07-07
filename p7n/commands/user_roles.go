package commands

import (
    "fmt"
    "io"
    "os"
    "golang.org/x/net/context"

    "github.com/spf13/cobra"
    "github.com/olekukonko/tablewriter"
    pb "github.com/jaypipes/procession/proto"
)

var (
    userRolesUserId string
)

var userRolesCommand = &cobra.Command{
    Use: "roles <user>",
    Short: "List roles for a user",
    RunE: userRoles,
}

func userRoles(cmd *cobra.Command, args []string) error {
    checkAuthUser(cmd)
    if len(args) != 1 {
        fmt.Println("Please specify a user identifier.")
        cmd.Usage()
        return nil
    }

    userRolesUserId = args[0]
    return userRolesList(cmd, userRolesUserId)
}

func userRolesList(cmd *cobra.Command, userId string) error {
    checkAuthUser(cmd)
    conn := connect()
    defer conn.Close()

    client := pb.NewIAMClient(conn)
    req := &pb.UserRolesListRequest{
        Session: &pb.Session{User: authUser},
        User: userId,
    }
    stream, err := client.UserRolesList(
        context.Background(),
        req,
    )
    if err != nil {
        return err
    }

    roles := make([]*pb.Role, 0)
    for {
        role, err := stream.Recv()
        if err == io.EOF {
            break
        }
        if err != nil {
            return err
        }
        roles = append(roles, role)
    }
    if len(roles) == 0 {
        exitNoRecords()
    }
    headers := []string{
        "UUID",
        "Display Name",
        "Slug",
        "Organization",
    }
    rows := make([][]string, len(roles))
    for x, role := range roles {
        orgUuid := ""
        if role.Organization != nil {
            orgUuid = role.Organization.Value
        }
        rows[x] = []string{
            role.Uuid,
            role.DisplayName,
            role.Slug,
            orgUuid,
        }
    }
    table := tablewriter.NewWriter(os.Stdout)
    table.SetHeader(headers)
    table.AppendBulk(rows)
    table.Render()
    return nil
}
