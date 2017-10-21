package commands

import (
	"os"
	"sort"

	"github.com/olekukonko/tablewriter"
	"github.com/spf13/cobra"

	pb "github.com/jaypipes/procession/proto"
)

var permissionsCommand = &cobra.Command{
	Use:   "permissions",
	Short: "Lists permissions that a role may have applied to it.",
	Run:   permissionsList,
}

type permRowComp func([]string, []string) bool

func (comp permRowComp) sort(rows [][]string) {
	ps := &permRowSorter{
		rows: rows,
		by:   comp,
	}
	sort.Sort(ps)
}

type permRowSorter struct {
	rows [][]string
	by   permRowComp
}

func (s *permRowSorter) Len() int {
	return len(s.rows)
}

func (s *permRowSorter) Swap(i, j int) {
	s.rows[i], s.rows[j] = s.rows[j], s.rows[i]
}

func (s *permRowSorter) Less(i, j int) bool {
	return s.by(s.rows[i], s.rows[j])
}

func permissionsList(cmd *cobra.Command, args []string) {
	headers := []string{
		"Permission",
	}
	rows := make([][]string, len(pb.Permission_value)-1)
	x := 0
	for perm, val := range pb.Permission_value {
		if pb.Permission(val) == pb.Permission_END_PERMS {
			continue
		}
		rows[x] = []string{perm}
		x++
	}
	byName := func(s1, s2 []string) bool {
		return s1[0] < s2[0]
	}
	permRowComp(byName).sort(rows)
	table := tablewriter.NewWriter(os.Stdout)
	table.SetHeader(headers)
	table.AppendBulk(rows)
	table.Render()
	return
}
