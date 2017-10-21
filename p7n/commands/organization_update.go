package commands

import (
	"fmt"
	"golang.org/x/net/context"
	"os"

	pb "github.com/jaypipes/procession/proto"
	"github.com/spf13/cobra"
)

var (
	orgUpdateDisplayName string
	orgUpdateParent      string
	orgUpdateVisibility  string
)

var orgUpdateCommand = &cobra.Command{
	Use:   "update <identifier>",
	Short: "Updates information for an organization",
	Run:   orgUpdate,
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
	orgUpdateCommand.Flags().StringVarP(
		&orgUpdateVisibility,
		"visibility", "",
		"PRIVATE",
		"Visibility of the organization (choices: PUBLIC, PRIVATE).",
	)
}

func init() {
	setupOrgUpdateFlags()
}

func orgUpdate(cmd *cobra.Command, args []string) {
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
	req.Changed.Visibility = checkVisibility(cmd, orgUpdateVisibility)
	resp, err := client.OrganizationSet(context.Background(), req)
	exitIfError(err)
	if !quiet {
		if !verbose {
			fmt.Println("OK")
		} else {
			org := resp.Organization
			fmt.Printf("Successfully saved organization %s\n", org.Uuid)
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
	}
}
