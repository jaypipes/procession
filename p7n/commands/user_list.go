package commands

import (
	"golang.org/x/net/context"
	"io"
	"os"
	"strings"

	pb "github.com/jaypipes/procession/proto"
	"github.com/olekukonko/tablewriter"
	"github.com/spf13/cobra"
)

var userListCommand = &cobra.Command{
	Use:   "list",
	Short: "List information about users",
	Run:   userList,
}

func setupUserListFlags() {
	addListOptions(userListCommand)
}

func init() {
	setupUserListFlags()
}

func userList(cmd *cobra.Command, args []string) {
	checkAuthUser(cmd)
	filters := &pb.UserListFilters{}
	if len(args) > 0 {
		filters.Identifiers = strings.Split(args[0], ",")
	}
	conn := connect()
	defer conn.Close()

	client := pb.NewIAMClient(conn)
	req := &pb.UserListRequest{
		Session: &pb.Session{User: authUser},
		Filters: filters,
		Options: buildSearchOptions(cmd),
	}
	stream, err := client.UserList(context.Background(), req)
	exitIfConnectErr(err)

	users := make([]*pb.User, 0)
	for {
		user, err := stream.Recv()
		if err == io.EOF {
			break
		}
		exitIfForbidden(err)
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
