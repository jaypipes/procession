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
    orgMembersListOrgId string
)

var orgMembersListCommand = &cobra.Command{
    Use: "members-list <organization>",
    Short: "List members of an organization",
    RunE: orgMembersList,
}

func orgMembersList(cmd *cobra.Command, args []string) error {
    if len(args) < 1 {
        fmt.Println("Please specify an organization identifier.")
        cmd.Usage()
        return nil
    }
    orgMembersListOrgId = args[0]
    conn, err := connect()
    if err != nil {
        return err
    }
    defer conn.Close()

    client := pb.NewIAMClient(conn)
    req := &pb.OrganizationMembersListRequest{
        Session: nil,
        Organization: orgMembersListOrgId,
    }
    stream, err := client.OrganizationMembersList(
        context.Background(),
        req,
    )
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
