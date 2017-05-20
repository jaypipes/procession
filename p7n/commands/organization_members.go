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
    orgMembersOrgId string
)

var orgMembersCommand = &cobra.Command{
    Use: "members <organization> [add|remove <users> ...]",
    Short: "List and change members of an organization",
    RunE: orgMembers,
}

func orgMembers(cmd *cobra.Command, args []string) error {
    if len(args) < 1 {
        fmt.Println("Please specify an organization identifier.")
        cmd.Usage()
        return nil
    }
    orgMembersOrgId = args[0]

    if len(args) == 1 {
        return orgMembersList(cmd, orgMembersOrgId)
    }
    return orgMembersSet(cmd, orgMembersOrgId, args[1:len(args)])
}

func orgMembersSet(cmd *cobra.Command, orgId string, args []string) error {
    toAdd := make([]string, 0)
    toRemove := make([]string, 0)
    for x := 0; x < len(args); x += 2 {
        arg := strings.TrimSpace(args[x])
        if (x + 1) < len(args) - 1 {
            fmt.Println("Expected either 'add' or 'remove' followed " +
                        "by comma-separated list of users to add or remove")
            cmd.Usage()
            return nil
        }
        if arg == "add" {
            toAdd = append(
                toAdd,
                strings.Split(
                    strings.TrimSpace(
                        args[x + 1],
                    ),
                    ",",
                )...,
            )
        } else if arg == "remove" {
            toRemove = append(
                toRemove,
                strings.Split(
                    strings.TrimSpace(
                        args[x + 1],
                    ),
                    ",",
                )...,
            )
        } else {
            fmt.Println("Unknown argument %s", arg)
            cmd.Usage()
            return nil
        }
    }

    conn, err := connect()
    if err != nil {
        return err
    }
    defer conn.Close()

    client := pb.NewIAMClient(conn)
    req := &pb.OrganizationMembersSetRequest{
        Session: &pb.Session{User: authUser},
        Organization: orgId,
    }
    if len(toAdd) > 0 {
        req.Add = toAdd
    }
    if len(toRemove) > 0 {
        req.Remove = toRemove
    }

    resp, err := client.OrganizationMembersSet(context.Background(), req)
    if err != nil {
        return err
    }
    printIf(verbose, "Added %d users to and %d users from %s\n",
            resp.NumAdded,
            resp.NumRemoved,
            orgId,
    )
    fmt.Println("OK")
    return nil

}

func orgMembersList(cmd *cobra.Command,orgId string) error {
    conn, err := connect()
    if err != nil {
        return err
    }
    defer conn.Close()

    client := pb.NewIAMClient(conn)
    req := &pb.OrganizationMembersListRequest{
        Session: nil,
        Organization: orgId,
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
