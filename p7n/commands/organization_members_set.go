package commands

import (
    "fmt"
    "strings"
    "golang.org/x/net/context"

    "github.com/spf13/cobra"
    pb "github.com/jaypipes/procession/proto"
)

var (
    orgMembersSetOrgId string
    orgMembersSetAdd string
    orgMembersSetRemove string
)

var orgMembersSetCommand = &cobra.Command{
    Use: "members-set <organization>",
    Short: "Manipulate user membership for an organization",
    RunE: orgMembersSet,
}

func setupOrganizationMembersSetFlags() {
    orgMembersSetCommand.PersistentFlags().StringVarP(
        &orgMembersSetAdd,
        "add", "",
        unsetSentinel,
        "Comma-delimited list of users to add to the organization.",
    )
    orgMembersSetCommand.PersistentFlags().StringVarP(
        &orgMembersSetRemove,
        "remove", "",
        unsetSentinel,
        "Comma-delimited list of users to remove from the organization.",
    )
}

func init() {
    setupOrganizationMembersSetFlags()
}

func orgMembersSet(cmd *cobra.Command, args []string) error {
    if len(args) < 1 {
        fmt.Println("Please specify an organization identifier.")
        cmd.Usage()
        return nil
    }
    orgMembersSetOrgId = args[0]
    conn, err := connect()
    if err != nil {
        return err
    }
    defer conn.Close()

    if (! isSet(orgMembersSetAdd) &&
            ! isSet(orgMembersSetRemove)) {
        msg := "Please specify users to add and/or remove from the organization."
        fmt.Println(msg)
        cmd.Usage()
        return nil
    }

    orgId := orgMembersSetOrgId
    client := pb.NewIAMClient(conn)
    req := &pb.OrganizationMembersSetRequest{
        Session: &pb.Session{User: authUser},
        Organization: orgId,
    }
    if isSet(orgMembersSetAdd) {
        req.Add = strings.Split(
            strings.TrimSpace(
                orgMembersSetAdd,
            ),
            ",",
        )
    }
    if isSet(orgMembersSetRemove) {
        req.Remove = strings.Split(
            strings.TrimSpace(
                orgMembersSetRemove,
            ),
            ",",
        )
    }

    resp, err := client.OrganizationMembersSet(context.Background(), req)
    if err != nil {
        return err
    }
    printIf(verbose, "Added %d users to and %d users from %s",
            resp.NumAdded,
            resp.NumRemoved,
            orgId,
    )
    fmt.Println("OK")
    return nil
}
