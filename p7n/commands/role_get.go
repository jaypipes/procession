package commands

import (
	"fmt"
	"os"
	"strings"

	"golang.org/x/net/context"

	pb "github.com/jaypipes/procession/proto"
	"github.com/spf13/cobra"
)

var roleGetCommand = &cobra.Command{
	Use:   "get <search>",
	Short: "Get information for a single role",
	Run:   roleGet,
}

func roleGet(cmd *cobra.Command, args []string) {
	checkAuthUser(cmd)
	if len(args) == 0 {
		fmt.Println("Please specify a UUID, name or slug to search for.")
		cmd.Usage()
		os.Exit(1)
	}
	conn := connect()
	defer conn.Close()

	client := pb.NewIAMClient(conn)
	req := &pb.RoleGetRequest{
		Session: &pb.Session{User: authUser},
		Search:  args[0],
	}
	role, err := client.RoleGet(context.Background(), req)
	exitIfError(err)
	if role.Uuid == "" {
		fmt.Printf("No role found matching request\n")
		os.Exit(1)
	}
	fmt.Printf("UUID:         %s\n", role.Uuid)
	if role.Organization != nil {
		orgUuid := role.Organization.Uuid
		orgName := role.Organization.DisplayName
		fmt.Printf("Organization: %s [%s]\n", orgName, orgUuid)
	}
	fmt.Printf("Display name: %s\n", role.DisplayName)
	fmt.Printf("Slug:         %s\n", role.Slug)
	if len(role.Permissions) > 0 {
		strPerms := make([]string, len(role.Permissions))
		for x, perm := range role.Permissions {
			strPerms[x] = perm.String()
		}
		permStr := strings.Join(strPerms, ", ")
		fmt.Printf("Permissions:  %s\n", permStr)
	} else {
		fmt.Printf("Permissions:  None\n")
	}
}
