package commands

import (
	"fmt"
	"golang.org/x/net/context"
	"os"

	pb "github.com/jaypipes/procession/proto"
	"github.com/spf13/cobra"
)

var (
	orgCreateDisplayName string
	orgCreateParent      string
	orgCreateVisibility  string
)

var orgCreateCommand = &cobra.Command{
	Use:   "create",
	Short: "Creates a new organization",
	Run:   orgCreate,
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
	orgCreateCommand.Flags().StringVarP(
		&orgCreateVisibility,
		"visibility", "",
		"PRIVATE",
		"Visibility of the organization (choices: PUBLIC, PRIVATE).",
	)
}

func init() {
	setupOrgCreateFlags()
}

func orgCreate(cmd *cobra.Command, args []string) {
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
	req.Changed.Visibility = checkVisibility(cmd, orgCreateVisibility)
	resp, err := client.OrganizationSet(context.Background(), req)
	exitIfError(err)
	org := resp.Organization
	if quiet {
		fmt.Println(org.Uuid)
	} else {
		fmt.Printf("Successfully created organization with UUID %s\n", org.Uuid)
	}
	if verbose {
		fmt.Printf("UUID:         %s\n", org.Uuid)
		fmt.Printf("Display name: %s\n", org.DisplayName)
		fmt.Printf("Slug:         %s\n", org.Slug)
		fmt.Printf("Visibility:   %s\n", org.Visibility)
		if org.Parent != nil {
			fmt.Printf(
				"Parent:       %s [%s]\n",
				org.Parent.DisplayName,
				org.Parent.Uuid,
			)
		}
	}
}
