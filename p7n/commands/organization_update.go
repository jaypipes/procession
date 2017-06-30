package commands

import (
    "fmt"
    "os"
    "golang.org/x/net/context"

    "github.com/spf13/cobra"
    pb "github.com/jaypipes/procession/proto"
)

var (
    orgUpdateDisplayName string
    orgUpdateParent string
)

var orgUpdateCommand = &cobra.Command{
    Use: "update <identifier>",
    Short: "Updates information for an organization",
    RunE: orgUpdate,
}

func setupOrgUpdateFlags() {
    orgUpdateCommand.Flags().StringVarP(
        &orgUpdateDisplayName,
        "display-name", "n",
        "",
        "Display name for the organization.",
    )
    orgUpdateCommand.Flags().StringVarP(
        &orgUpdateParent,
        "parent", "",
        "",
        "The parent organization, if any.",
    )
}

func init() {
    setupOrgUpdateFlags()
}

func orgUpdate(cmd *cobra.Command, args []string) error {
    checkAuthUser(cmd)
    conn := connect()
    defer conn.Close()

    client := pb.NewIAMClient(conn)
    req := &pb.OrganizationSetRequest{
        Session: &pb.Session{User: authUser},
        Changed: &pb.OrganizationSetFields{},
    }

    if len(args) != 1 {
        fmt.Println("Please specify an organization identifier.")
        cmd.Usage()
        os.Exit(1)
    } else {
        req.Search = &pb.StringValue{Value: args[0]}
    }

    if cmd.Flags().Changed("display-name") {
        req.Changed.DisplayName = &pb.StringValue{
            Value: orgUpdateDisplayName,
        }
    }
    if cmd.Flags().Changed("parent") {
        req.Changed.Parent = &pb.StringValue{
            Value: orgUpdateParent,
        }
    }
    resp, err := client.OrganizationSet(context.Background(), req)
    if err != nil {
        return err
    }
    org := resp.Organization
    fmt.Printf("Successfully saved organization %s\n", org.Uuid)
    fmt.Printf("UUID:         %s\n", org.Uuid)
    fmt.Printf("Display name: %s\n", org.DisplayName)
    fmt.Printf("Slug:         %s\n", org.Slug)
    if org.ParentUuid != nil {
        fmt.Printf("Parent:       %s\n", org.ParentUuid.Value)
    }
    return nil
}
