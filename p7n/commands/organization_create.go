package commands

import (
    "fmt"
    "os"
    "golang.org/x/net/context"

    "github.com/spf13/cobra"
    pb "github.com/jaypipes/procession/proto"
)

var (
    orgCreateDisplayName string
    orgCreateParent string
)

var orgCreateCommand = &cobra.Command{
    Use: "create",
    Short: "Creates a new organization",
    RunE: orgCreate,
}

func setupOrgCreateFlags() {
    orgCreateCommand.Flags().StringVarP(
        &orgCreateDisplayName,
        "display-name", "n",
        "",
        "Display name for the organization.",
    )
    orgCreateCommand.Flags().StringVarP(
        &orgCreateParent,
        "parent", "",
        "",
        "The parent organization, if any.",
    )
}

func init() {
    setupOrgCreateFlags()
}

func orgCreate(cmd *cobra.Command, args []string) error {
    checkAuthUser(cmd)
    conn := connect()
    defer conn.Close()

    client := pb.NewIAMClient(conn)
    req := &pb.OrganizationSetRequest{
        Session: &pb.Session{User: authUser},
        Changed: &pb.OrganizationSetFields{},
    }

    if cmd.Flags().Changed("display-name") {
        req.Changed.DisplayName = &pb.StringValue{
            Value: orgCreateDisplayName,
        }
    } else {
        fmt.Println("Specify a display name using --display-name=<NAME>.")
        cmd.Usage()
        os.Exit(1)
    }
    if cmd.Flags().Changed("parent") {
        req.Changed.Parent = &pb.StringValue{
            Value: orgCreateParent,
        }
    }
    resp, err := client.OrganizationSet(context.Background(), req)
    if err != nil {
        return err
    }
    org := resp.Organization
    if quiet {
        fmt.Println(org.Uuid)
    } else {
        fmt.Printf("Successfully created organization with UUID %s\n", org.Uuid)
        fmt.Printf("UUID:         %s\n", org.Uuid)
        fmt.Printf("Display name: %s\n", org.DisplayName)
        fmt.Printf("Slug:         %s\n", org.Slug)
        if org.Parent != nil {
            fmt.Printf(
                "Parent:       %s [%s]\n",
                org.Parent.DisplayName,
                org.Parent.Uuid,
            )
        }
    }
    return nil
}
