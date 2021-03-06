package commands

import (
	"fmt"
	"golang.org/x/net/context"
	"io"
	"os"
	"strings"

	pb "github.com/jaypipes/procession/proto"
	"github.com/olekukonko/tablewriter"
	"github.com/spf13/cobra"
)

var (
	orgMembersOrgId string
)

var orgMembersCommand = &cobra.Command{
	Use:   "members <organization> [add|remove <users> ...]",
	Short: "List and change members of an organization",
	Run:   orgMembers,
}

func orgMembers(cmd *cobra.Command, args []string) {
	checkAuthUser(cmd)
	if len(args) < 1 {
		fmt.Println("Please specify an organization identifier.")
		cmd.Usage()
		os.Exit(1)
	}
	orgMembersOrgId = args[0]

	if len(args) == 1 {
		orgMembersList(cmd, orgMembersOrgId)
	} else {
		orgMembersSet(cmd, orgMembersOrgId, args[1:len(args)])
	}
}

func orgMembersSet(cmd *cobra.Command, orgId string, args []string) {
	toAdd := make([]string, 0)
	toRemove := make([]string, 0)
	for x := 0; x < len(args); x += 2 {
		arg := strings.TrimSpace(args[x])
		if len(args) <= (x + 1) {
			fmt.Println("Expected either 'add' or 'remove' followed " +
				"by comma-separated list of users to add or remove")
			cmd.Usage()
			os.Exit(1)
		}
		if arg == "add" {
			toAdd = append(
				toAdd,
				strings.Split(
					strings.TrimSpace(
						args[x+1],
					),
					",",
				)...,
			)
		} else if arg == "remove" {
			toRemove = append(
				toRemove,
				strings.Split(
					strings.TrimSpace(
						args[x+1],
					),
					",",
				)...,
			)
		} else {
			fmt.Printf("Unknown argument '%s'\n", arg)
			fmt.Println("Expected either 'add' or 'remove' followed " +
				"by comma-separated list of users to add or remove")
			cmd.Usage()
			os.Exit(1)
		}
	}

	conn := connect()
	defer conn.Close()

	client := pb.NewIAMClient(conn)
	req := &pb.OrganizationMembersSetRequest{
		Session:      &pb.Session{User: authUser},
		Organization: orgId,
	}
	if len(toAdd) > 0 {
		req.Add = toAdd
	}
	if len(toRemove) > 0 {
		req.Remove = toRemove
	}

	resp, err := client.OrganizationMembersSet(context.Background(), req)
	exitIfError(err)
	printIf(verbose, "Added %d users to and removed %d users from %s\n",
		resp.NumAdded,
		resp.NumRemoved,
		orgId,
	)
	printIf(!quiet, "OK\n")
}

func orgMembersList(cmd *cobra.Command, orgId string) {
	conn := connect()
	defer conn.Close()

	client := pb.NewIAMClient(conn)
	req := &pb.OrganizationMembersListRequest{
		Session:      &pb.Session{User: authUser},
		Organization: orgId,
	}
	stream, err := client.OrganizationMembersList(
		context.Background(),
		req,
	)
	exitIfError(err)

	users := make([]*pb.User, 0)
	for {
		user, err := stream.Recv()
		if err == io.EOF {
			break
		}
		exitIfError(err)
		users = append(users, user)
	}
	if len(users) == 0 {
		exitNoRecords()
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
}
