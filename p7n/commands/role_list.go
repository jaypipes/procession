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
	roleListOrganization string
)

var roleListCommand = &cobra.Command{
	Use:   "list",
	Short: "List information about roles",
	Run:   roleList,
}

func setupRoleListFlags() {
	roleListCommand.Flags().StringVarP(
		&roleListOrganization,
		"organization", "",
		"",
		"Comma-delimited list of organization identifiers to filter by.",
	)
	addListOptions(roleListCommand)
}

func init() {
	setupRoleListFlags()
}

func roleList(cmd *cobra.Command, args []string) {
	checkAuthUser(cmd)
	filters := &pb.RoleListFilters{}
	if len(args) > 0 {
		filters.Identifiers = strings.Split(args[0], ",")
	}
	if cmd.Flags().Changed("organization") {
		filters.Organizations = strings.Split(roleListOrganization, ",")
	}
	conn := connect()
	defer conn.Close()

	client := pb.NewIAMClient(conn)
	req := &pb.RoleListRequest{
		Session: &pb.Session{User: authUser},
		Filters: filters,
		Options: buildSearchOptions(cmd),
	}
	stream, err := client.RoleList(context.Background(), req)
	exitIfConnectErr(err)

	roles := make([]*pb.Role, 0)
	for {
		role, err := stream.Recv()
		if err == io.EOF {
			break
		}
		exitIfError(err)
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
		org := ""
		if role.Organization != nil {
			org = fmt.Sprintf(
				"%s",
				role.Organization.DisplayName,
			)
		}
		rows[x] = []string{
			role.Uuid,
			role.DisplayName,
			role.Slug,
			org,
		}
	}
	table := tablewriter.NewWriter(os.Stdout)
	table.SetHeader(headers)
	table.AppendBulk(rows)
	table.Render()
}
