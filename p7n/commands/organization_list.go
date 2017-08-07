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
    orgListShowTree bool
)

var orgListCommand = &cobra.Command{
    Use: "list [<identifier>,...]",
    Short: "List information about organizations",
    Run: orgList,
}

func setupOrgListFlags() {
    orgListCommand.Flags().BoolVarP(
        &orgListShowTree,
        "tree", "t",
        false,
        "Show orgs in a tree view.",
    )
    addListOptions(orgListCommand)
}

func init() {
    setupOrgListFlags()
}

func orgList(cmd *cobra.Command, args []string) {
    checkAuthUser(cmd)
    filters := &pb.OrganizationListFilters{}
    if len(args) > 0 {
        filters.Identifiers = strings.Split(args[0], ",")
    }
    conn := connect()
    defer conn.Close()

    client := pb.NewIAMClient(conn)
    req := &pb.OrganizationListRequest{
        Session: &pb.Session{User: authUser},
        Filters: filters,
        Options: buildSearchOptions(cmd),
    }
    stream, err := client.OrganizationList(context.Background(), req)
    exitIfError(err)

    orgs := make([]*pb.Organization, 0)
    for {
        org, err := stream.Recv()
        if err == io.EOF {
            break
        }
        exitIfForbidden(err)
        exitIfError(err)
        orgs = append(orgs, org)
    }
    if len(orgs) == 0 {
        exitNoRecords()
    }
    if ! orgListShowTree {
        orgListViewTable(&orgs)
    } else {
        orgListViewTree(&orgs)
    }
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
        parent := ""
        if org.Parent != nil {
            parent = org.Parent.DisplayName
        }
        rows[x] = []string{
            org.Uuid,
            org.DisplayName,
            org.Slug,
            parent,
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

// Returns a node in the tree matching the supplied UUID
func (n *orgTreeNode) find(uuid string) *orgTreeNode {
    if n.node.Uuid == uuid {
        return n
    }
    for _, child := range n.children {
        found := child.find(uuid)
        if found != nil {
            return found
        }
    }
    return nil
}

func (n *orgTreeNode) addChild(child *orgTreeNode) {
    n.children = append(n.children, child)
}

func (n *orgTreeNode) printNode(level int, last bool) {
    endCap := ""
    if level > 0 {
        endCap = "└"
    }
    prefix := ""
    if level > 0 {
        prefix = strings.Repeat("    ", level)
        prefix = prefix[0:len(prefix) - 1]
    }
    branch := fmt.Sprintf("%s%s", prefix, endCap)
    fmt.Printf("%s── %s (%s)\n",
        branch,
        n.node.DisplayName,
        n.node.Uuid,
    )
    if len(n.children) > 0 {
        level++
        for x, child := range n.children {
            child.printNode(level, x == (len(n.children) - 1))
        }
    }
}

func orgListViewTree(orgs *[]*pb.Organization) {
    t := orgTree{}
    t.roots = make([]*orgTreeNode, 0)
    // Allows us to make a single pass through all the organization records...
    missingParents := make(map[string][]*orgTreeNode)
    for _, o := range *orgs {
        n := &orgTreeNode{
            node: o,
            children: make([]*orgTreeNode, 0),
        }
        if o.Parent == nil {
            t.roots = append(t.roots, n)
        } else {
            parentUuid := o.Parent.Uuid
            for _, r := range t.roots {
                foundParent := r.find(parentUuid)
                if foundParent != nil {
                    foundParent.addChild(n)
                } else {
                    if _, ok := missingParents[parentUuid]; ! ok {
                        missingParents[parentUuid] = make([]*orgTreeNode, 1)
                        missingParents[parentUuid][0] = n
                    } else {
                        missingParents[parentUuid] = append(missingParents[parentUuid], n)
                    }
                }
                // Handle any previously-missed children
                if _, ok := missingParents[o.Uuid]; ok {
                    for _, child := range missingParents[o.Uuid] {
                        n.addChild(child)
                    }
                }
            }
        }
    }
    for x, r := range t.roots {
        r.printNode(0, x == (len(t.roots) - 1))
    }
}
