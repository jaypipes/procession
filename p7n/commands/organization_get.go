package commands

import (
	"fmt"
	"os"

	"golang.org/x/net/context"

	pb "github.com/jaypipes/procession/proto"
	"github.com/spf13/cobra"
)

var orgGetCommand = &cobra.Command{
	Use:   "get <search>",
	Short: "Get information for a single organization",
	Run:   orgGet,
}

func orgGet(cmd *cobra.Command, args []string) {
	checkAuthUser(cmd)
	if len(args) == 0 {
		fmt.Println("Please specify a UUID, name or slug to search for.")
		cmd.Usage()
		os.Exit(1)
	}
	conn := connect()
	defer conn.Close()

	client := pb.NewIAMClient(conn)
	req := &pb.OrganizationGetRequest{
		Session: &pb.Session{User: authUser},
		Search:  args[0],
	}
	org, err := client.OrganizationGet(context.Background(), req)
	exitIfError(err)
	if org.Uuid == "" {
		fmt.Printf("No organization found matching request\n")
		os.Exit(1)
	}
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
