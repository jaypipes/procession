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
    listOrganizationsUuid string
    listOrganizationsDisplayName string
    listOrganizationsSlug string
    listOrganizationsShowTree bool
)

var organizationListCommand = &cobra.Command{
    Use: "list",
    Short: "List information about organizations",
    RunE: listOrganizations,
}

func addOrganizationListFlags() {
    organizationListCommand.Flags().StringVarP(
        &listOrganizationsUuid,
        "uuid", "u",
        unsetSentinel,
        "Comma-separated list of UUIDs to filter by",
    )
    organizationListCommand.Flags().StringVarP(
        &listOrganizationsDisplayName,
        "display-name", "n",
        unsetSentinel,
        "Comma-separated list of display names to filter by",
    )
    organizationListCommand.Flags().StringVarP(
        &listOrganizationsSlug,
        "slug", "",
        unsetSentinel,
        "Comma-delimited list of slugs to filter by.",
    )
    organizationListCommand.Flags().BoolVarP(
        &listOrganizationsShowTree,
        "tree", "t",
        false,
        "Show organizations in a tree view.",
    )
}

func init() {
    addOrganizationListFlags()
}

func listOrganizations(cmd *cobra.Command, args []string) error {
    filters := &pb.ListOrganizationsFilters{}
    if isSet(listOrganizationsUuid) {
        filters.Uuids = strings.Split(listOrganizationsUuid, ",")
    }
    if isSet(listOrganizationsDisplayName) {
        filters.DisplayNames = strings.Split(listOrganizationsDisplayName, ",")
    }
    if isSet(listOrganizationsSlug) {
        filters.Slugs = strings.Split(listOrganizationsSlug, ",")
    }
    conn, err := connect()
    if err != nil {
        return err
    }
    defer conn.Close()

    client := pb.NewIAMClient(conn)
    req := &pb.ListOrganizationsRequest{
        Session: nil,
        Filters: filters,
    }
    stream, err := client.ListOrganizations(context.Background(), req)
    if err != nil {
        return err
    }

    organizations := make([]*pb.Organization, 0)
    for {
        organization, err := stream.Recv()
        if err == io.EOF {
            break
        }
        if err != nil {
            return err
        }
        organizations = append(organizations, organization)
    }
    if ! listOrganizationsShowTree {
        printOrganizationsTable(&organizations)
    } else {
        printOrganizationsTree(&organizations)
    }
    return nil
}

func printOrganizationsTable(organizations *[]*pb.Organization) {
    headers := []string{
        "UUID",
        "Display Name",
        "Slug",
        "Parent",
    }
    rows := make([][]string, len(*organizations))
    for x, organization := range *organizations {
        parentUuid := ""
        if organization.ParentOrganizationUuid != nil {
            parentUuid = organization.ParentOrganizationUuid.Value
        }
        rows[x] = []string{
            organization.Uuid,
            organization.DisplayName,
            organization.Slug,
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

func printOrganizationsTree(organizations *[]*pb.Organization) {
    t := orgTree{}
    t.roots = make([]*orgTreeNode, 0)
    for _, o := range *organizations {
        n := &orgTreeNode{
            node: o,
            children: make([]*orgTreeNode, 0),
        }
        if o.ParentOrganizationUuid == nil {
            t.roots = append(t.roots, n)
        } else {
            parentUuid := o.ParentOrganizationUuid.Value
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
