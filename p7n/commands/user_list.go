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
    listUsersUuid string
    listUsersDisplayName string
    listUsersEmail string
    listUsersSlug string
)

var userListCommand = &cobra.Command{
    Use: "list",
    Short: "List information about users",
    RunE: listUsers,
}

func addUserListFlags() {
    userListCommand.Flags().StringVarP(
        &listUsersUuid,
        "uuid", "u",
        unsetSentinel,
        "Comma-separated list of UUIDs to filter by",
    )
    userListCommand.Flags().StringVarP(
        &listUsersDisplayName,
        "display-name", "n",
        unsetSentinel,
        "Comma-separated list of display names to filter by",
    )
    userListCommand.Flags().StringVarP(
        &listUsersEmail,
        "email", "e",
        unsetSentinel,
        "Comma-separated list of emails to filter by.",
    )
    userListCommand.Flags().StringVarP(
        &listUsersSlug,
        "slug", "",
        unsetSentinel,
        "Comma-delimited list of slugs to filter by.",
    )
}

func init() {
    addUserListFlags()
}

func listUsers(cmd *cobra.Command, args []string) error {
    filters := &pb.ListUsersFilters{}
    if isSet(listUsersUuid) {
        filters.Uuids = strings.Split(listUsersUuid, ",")
    }
    if isSet(listUsersDisplayName) {
        filters.DisplayNames = strings.Split(listUsersDisplayName, ",")
    }
    if isSet(listUsersEmail) {
        filters.Emails = strings.Split(listUsersEmail, ",")
    }
    if isSet(listUsersSlug) {
        filters.Slugs = strings.Split(listUsersSlug, ",")
    }
    conn, err := connect()
    if err != nil {
        return err
    }
    defer conn.Close()

    client := pb.NewIAMClient(conn)
    req := &pb.ListUsersRequest{
        Session: nil,
        Filters: filters,
    }
    stream, err := client.ListUsers(context.Background(), req)
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

