package commands

import (
    "io"
    "os"
    "strings"
    "golang.org/x/net/context"

    "github.com/spf13/cobra"
    "github.com/olekukonko/tablewriter"
    pb "github.com/jaypipes/procession/proto"
)

var (
    userListUuid string
    userListDisplayName string
    userListEmail string
    userListSlug string
)

var userListCommand = &cobra.Command{
    Use: "list",
    Short: "List information about users",
    RunE: userList,
}

func setupUserListFlags() {
    userListCommand.Flags().StringVarP(
        &userListUuid,
        "uuid", "u",
        "",
        "Comma-separated list of UUIDs to filter by",
    )
    userListCommand.Flags().StringVarP(
        &userListDisplayName,
        "display-name", "n",
        "",
        "Comma-separated list of display names to filter by",
    )
    userListCommand.Flags().StringVarP(
        &userListEmail,
        "email", "e",
        "",
        "Comma-separated list of emails to filter by.",
    )
    userListCommand.Flags().StringVarP(
        &userListSlug,
        "slug", "",
        "",
        "Comma-delimited list of slugs to filter by.",
    )
}

func init() {
    setupUserListFlags()
}

func userList(cmd *cobra.Command, args []string) error {
    checkAuthUser(cmd)
    filters := &pb.UserListFilters{}
    if cmd.Flags().Changed("uuid") {
        filters.Uuids = strings.Split(userListUuid, ",")
    }
    if cmd.Flags().Changed("display-name") {
        filters.DisplayNames = strings.Split(userListDisplayName, ",")
    }
    if cmd.Flags().Changed("email") {
        filters.Emails = strings.Split(userListEmail, ",")
    }
    if cmd.Flags().Changed("slug") {
        filters.Slugs = strings.Split(userListSlug, ",")
    }
    conn := connect()
    defer conn.Close()

    client := pb.NewIAMClient(conn)
    req := &pb.UserListRequest{
        Session: &pb.Session{User: authUser},
        Filters: filters,
    }
    stream, err := client.UserList(context.Background(), req)
    exitIfConnectErr(err)

    users := make([]*pb.User, 0)
    for {
        user, err := stream.Recv()
        if err == io.EOF {
            break
        }
        if err != nil {
            return err
        }
        users = append(users, user)
    }
    if len(users) == 0 {
        exitNoRecords()
    }
    headers := []string{
        "UUID",
        "Display Name",
        "Email",
        "Slug",
    }
    rows := make([][]string, len(users))
    for x, user := range users {
        rows[x] = []string{
            user.Uuid,
            user.DisplayName,
            user.Email,
            user.Slug,
        }
    }
    table := tablewriter.NewWriter(os.Stdout)
    table.SetHeader(headers)
    table.AppendBulk(rows)
    table.Render()
    return nil
}
