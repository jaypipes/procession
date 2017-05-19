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
        unsetSentinel,
        "Comma-separated list of UUIDs to filter by",
    )
    userListCommand.Flags().StringVarP(
        &userListDisplayName,
        "display-name", "n",
        unsetSentinel,
        "Comma-separated list of display names to filter by",
    )
    userListCommand.Flags().StringVarP(
        &userListEmail,
        "email", "e",
        unsetSentinel,
        "Comma-separated list of emails to filter by.",
    )
    userListCommand.Flags().StringVarP(
        &userListSlug,
        "slug", "",
        unsetSentinel,
        "Comma-delimited list of slugs to filter by.",
    )
}

func init() {
    setupUserListFlags()
}

func userList(cmd *cobra.Command, args []string) error {
    filters := &pb.UserListFilters{}
    if isSet(userListUuid) {
        filters.Uuids = strings.Split(userListUuid, ",")
    }
    if isSet(userListDisplayName) {
        filters.DisplayNames = strings.Split(userListDisplayName, ",")
    }
    if isSet(userListEmail) {
        filters.Emails = strings.Split(userListEmail, ",")
    }
    if isSet(userListSlug) {
        filters.Slugs = strings.Split(userListSlug, ",")
    }
    conn, err := connect()
    if err != nil {
        return err
    }
    defer conn.Close()

    client := pb.NewIAMClient(conn)
    req := &pb.UserListRequest{
        Session: nil,
        Filters: filters,
    }
    stream, err := client.UserList(context.Background(), req)
    if err != nil {
        return err
    }

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
