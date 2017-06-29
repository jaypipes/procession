package commands

import (
    "fmt"
    "golang.org/x/net/context"

    "github.com/spf13/cobra"
    pb "github.com/jaypipes/procession/proto"
)

var roleDeleteCommand = &cobra.Command{
    Use: "delete <role>",
    Short: "Deletes a role and all of its associated permissions and users",
    RunE: roleDelete,
}

func roleDelete(cmd *cobra.Command, args []string) error {
    checkAuthUser(cmd)
    if len(args) != 1 {
        fmt.Println("Please specify a role identifier.")
        cmd.Usage()
        return nil
    }
    conn := connect()
    defer conn.Close()

    roleId := args[0]
    client := pb.NewIAMClient(conn)
    req := &pb.RoleDeleteRequest{
        Session: &pb.Session{User: authUser},
        Search: roleId,
    }

    _, err := client.RoleDelete(context.Background(), req)
    if err != nil {
        return err
    }
    if ! quiet {
        fmt.Printf("Successfully deleted role %s\n", roleId)
    }
    return nil
}
