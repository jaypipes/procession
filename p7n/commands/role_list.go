package commands

import (
    "fmt"
    "io"
    "os"
    "strings"
    "golang.org/x/net/context"

    "github.com/spf13/cobra"
    "github.com/olekukonko/tablewriter"
    pb "github.com/jaypipes/procession/proto"
)

var (
    roleListUuid string
    roleListDisplayName string
    roleListSlug string
)

var roleListCommand = &cobra.Command{
    Use: "list",
    Short: "List information about roles",
    RunE: roleList,
}

func setupRoleListFlags() {
    roleListCommand.Flags().StringVarP(
        &roleListUuid,
        "uuid", "u",
        "",
        "Comma-separated list of UUIDs to filter by",
    )
    roleListCommand.Flags().StringVarP(
        &roleListDisplayName,
        "display-name", "n",
        "",
        "Comma-separated list of display names to filter by",
    )
    roleListCommand.Flags().StringVarP(
        &roleListSlug,
        "slug", "",
        "",
        "Comma-delimited list of slugs to filter by.",
    )
}

func init() {
    setupRoleListFlags()
}

func roleList(cmd *cobra.Command, args []string) error {
    checkAuthUser(cmd)
    filters := &pb.RoleListFilters{}
    if cmd.Flags().Changed("uuid") {
        filters.Uuids = strings.Split(roleListUuid, ",")
    }
    if cmd.Flags().Changed("display-name") {
        filters.DisplayNames = strings.Split(roleListDisplayName, ",")
    }
    if cmd.Flags().Changed("slug") {
        filters.Slugs = strings.Split(roleListSlug, ",")
    }
    conn := connect()
    defer conn.Close()

    client := pb.NewIAMClient(conn)
    req := &pb.RoleListRequest{
        Session: &pb.Session{User: authUser},
        Filters: filters,
    }
    stream, err := client.RoleList(context.Background(), req)
    exitIfConnectErr(err)

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
        if ! quiet {
            fmt.Println("No records found matching search criteria.")
        }
        return nil
    }
    headers := []string{
        "UUID",
        "Display Name",
        "Slug",
    }
    rows := make([][]string, len(roles))
    for x, role := range roles {
        rows[x] = []string{
            role.Uuid,
            role.DisplayName,
            role.Slug,
        }
    }
    table := tablewriter.NewWriter(os.Stdout)
    table.SetHeader(headers)
    table.AppendBulk(rows)
    table.Render()
    return nil
}
