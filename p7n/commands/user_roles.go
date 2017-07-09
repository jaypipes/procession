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
    userRolesUserId string
)

var userRolesCommand = &cobra.Command{
    Use: "roles <user> [add|remove <roles> ...]",
    Short: "List and change roles for a user",
    RunE: userRoles,
}

func userRoles(cmd *cobra.Command, args []string) error {
    checkAuthUser(cmd)
    if len(args) < 1 {
        fmt.Println("Please specify a user identifier.")
        cmd.Usage()
        return nil
    }

    userRolesUserId = args[0]
    if len(args) == 1 {
        return userRolesList(cmd, userRolesUserId)
    }
    return userRolesSet(cmd, userRolesUserId, args[1:len(args)])
}

func userRolesSet(cmd *cobra.Command, userId string, args []string) error {
    checkAuthUser(cmd)
    toAdd := make([]string, 0)
    toRemove := make([]string, 0)
    for x := 0; x < len(args); x += 2 {
        arg := strings.TrimSpace(args[x])
        if (x + 1) < len(args) - 1 {
            fmt.Println("Expected either 'add' or 'remove' followed " +
                        "by comma-separated list of roles to add or remove")
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

    conn := connect()
    defer conn.Close()

    client := pb.NewIAMClient(conn)
    req := &pb.UserRolesSetRequest{
        Session: &pb.Session{User: authUser},
        User: userId,
    }
    if len(toAdd) > 0 {
        req.Add = toAdd
    }
    if len(toRemove) > 0 {
        req.Remove = toRemove
    }

    resp, err := client.UserRolesSet(context.Background(), req)
    if err != nil {
        return err
    }
    printIf(verbose, "Added %d roles to and removed %d roles from %s\n",
            resp.NumAdded,
            resp.NumRemoved,
            userId,
    )
    printIf(! quiet, "OK\n")
    return nil
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
