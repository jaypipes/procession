package commands

import (
    "fmt"
    "io"
    "os"
    "strings"
    "golang.org/x/net/context"

    "github.com/spf13/cobra"
    "github.com/olekukonko/tablewriter"
    pb "github.com/jaypipes/procession/proto"
)

var (
    orgListUuid string
    orgListDisplayName string
    orgListSlug string
    orgListShowTree bool
)

var orgListCommand = &cobra.Command{
    Use: "list",
    Short: "List information about organizations",
    RunE: orgList,
}

func setupOrgListFlags() {
    orgListCommand.Flags().StringVarP(
        &orgListUuid,
        "uuid", "u",
        unsetSentinel,
        "Comma-separated list of UUIDs to filter by",
    )
    orgListCommand.Flags().StringVarP(
        &orgListDisplayName,
        "display-name", "n",
        unsetSentinel,
        "Comma-separated list of display names to filter by",
    )
    orgListCommand.Flags().StringVarP(
        &orgListSlug,
        "slug", "",
        unsetSentinel,
        "Comma-delimited list of slugs to filter by.",
    )
    orgListCommand.Flags().BoolVarP(
        &orgListShowTree,
        "tree", "t",
        false,
        "Show orgs in a tree view.",
    )
}

func init() {
    setupOrgListFlags()
}

func orgList(cmd *cobra.Command, args []string) error {
    filters := &pb.OrganizationListFilters{}
    if isSet(orgListUuid) {
        filters.Uuids = strings.Split(orgListUuid, ",")
    }
    if isSet(orgListDisplayName) {
        filters.DisplayNames = strings.Split(orgListDisplayName, ",")
    }
    if isSet(orgListSlug) {
        filters.Slugs = strings.Split(orgListSlug, ",")
    }
    conn, err := connect()
    if err != nil {
        return err
    }
    defer conn.Close()

    client := pb.NewIAMClient(conn)
    req := &pb.OrganizationListRequest{
        Session: nil,
        Filters: filters,
    }
    stream, err := client.OrganizationList(context.Background(), req)
    if err != nil {
        return err
    }

    orgs := make([]*pb.Organization, 0)
    for {
        org, err := stream.Recv()
        if err == io.EOF {
            break
        }
        if err != nil {
            return err
        }
        orgs = append(orgs, org)
    }
    if ! orgListShowTree {
        orgListViewTable(&orgs)
    } else {
        orgListViewTree(&orgs)
    }
    return nil
}

func orgListViewTable(orgs *[]*pb.Organization) {
    headers := []string{
        "UUID",
        "Display Name",
        "Slug",
        "Parent",
    }
    rows := make([][]string, len(*orgs))
    for x, org := range *orgs {
        parentUuid := ""
        if org.ParentUuid != nil {
            parentUuid = org.ParentUuid.Value
        }
        rows[x] = []string{
            org.Uuid,
            org.DisplayName,
            org.Slug,
            parentUuid,
        }
    }
    table := tablewriter.NewWriter(os.Stdout)
    table.SetHeader(headers)
    table.AppendBulk(rows)
    table.Render()
}

type orgTreeNode struct {
    node *pb.Organization
    children []*orgTreeNode
}

type orgTree struct {
    roots []*orgTreeNode
}

func (n *orgTreeNode) printNode(indent int, first bool) {
    indentStr := ""
    if indent > 0 {
        repeated := strings.Repeat("  ", indent - 1)
        if first {
            indentStr = fmt.Sprintf("%s-> ", repeated)
        } else {
            indentStr = fmt.Sprintf("%s   ", repeated)
        }
    }
    fmt.Printf("%s%s (%s)\n",
        indentStr,
        n.node.DisplayName,
        n.node.Uuid,
    )
    if len(n.children) > 0 {
        indent++
        for x, child := range n.children {
            child.printNode(indent, x == 0)
        }
    }
}

func orgListViewTree(orgs *[]*pb.Organization) {
    t := orgTree{}
    t.roots = make([]*orgTreeNode, 0)
    for _, o := range *orgs {
        n := &orgTreeNode{
            node: o,
            children: make([]*orgTreeNode, 0),
        }
        if o.ParentUuid == nil {
            t.roots = append(t.roots, n)
        } else {
            parentUuid := o.ParentUuid.Value
            for _, r := range t.roots {
                if parentUuid == r.node.Uuid {
                    r.children = append(r.children, n)
                }
            }
        }
    }
    for _, r := range t.roots {
        r.printNode(0, true)
    }
}
