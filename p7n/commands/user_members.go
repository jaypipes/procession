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
    userMembersUserId string
)

var userMembersCommand = &cobra.Command{
    Use: "members <user>",
    Short: "List organizations this user is a member of",
    Run: userMembers,
}

func userMembers(cmd *cobra.Command, args []string) {
    checkAuthUser(cmd)
    if len(args) != 1 {
        fmt.Println("Please specify a user identifier.")
        cmd.Usage()
        os.Exit(1)
    }

    userMembersUserId = args[0]
    userMembersList(cmd, userMembersUserId)
}

func userMembersList(cmd *cobra.Command, userId string) {
    checkAuthUser(cmd)
    conn := connect()
    defer conn.Close()

    client := pb.NewIAMClient(conn)
    req := &pb.UserMembersListRequest{
        Session: &pb.Session{User: authUser},
        User: userId,
    }
    stream, err := client.UserMembersList(
        context.Background(),
        req,
    )
    exitIfError(err)

    orgs := make([]*pb.Organization, 0)
    for {
        org, err := stream.Recv()
        if err == io.EOF {
            break
        }
        exitIfError(err)
        orgs = append(orgs, org)
    }
    if len(orgs) == 0 {
        exitNoRecords()
    }
    headers := []string{
        "UUID",
        "Display Name",
        "Slug",
        "Parent",
    }
    rows := make([][]string, len(orgs))
    for x, org := range orgs {
        parent := ""
        if org.Parent != nil {
            parent = org.Parent.DisplayName
        }
        rows[x] = []string{
            org.Uuid,
            org.DisplayName,
            org.Slug,
            parent,
        }
    }
    table := tablewriter.NewWriter(os.Stdout)
    table.SetHeader(headers)
    table.AppendBulk(rows)
    table.Render()
}
