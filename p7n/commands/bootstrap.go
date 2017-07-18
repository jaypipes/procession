package commands

import (
    "fmt"
    "os"
    "strings"

    "golang.org/x/net/context"

    "github.com/spf13/cobra"
    pb "github.com/jaypipes/procession/proto"
)

var (
    bootstrapKey string
    bootstrapSuperUserEmails string
    bootstrapSuperRoleName string
)

var bootstrapCommand = &cobra.Command{
    Use: "bootstrap",
    Short: "Perform bootstrap actions",
    RunE: bootstrap,
}

func setupBootstrapFlags() {
    bootstrapCommand.Flags().StringVarP(
        &bootstrapKey,
        "key", "k",
        "",
        "The bootstrapping key.",
    )
    bootstrapCommand.Flags().StringVarP(
        &bootstrapSuperUserEmails,
        "super-user-email", "",
        "",
        "Comma-delimited list of emails to create super user accounts for.",
    )
    bootstrapCommand.Flags().StringVarP(
        &bootstrapSuperRoleName,
        "super-role-name", "k",
        "admins",
        "The name to use for a role containing the SUPER privilege.",
    )
}

func init() {
    setupBootstrapFlags()
}

func bootstrap(cmd *cobra.Command, args []string) error {
    conn := connect()
    defer conn.Close()

    client := pb.NewIAMClient(conn)
    req := &pb.BootstrapRequest{}

    if cmd.Flags().Changed("key") {
        req.Key = bootstrapKey
    } else {
        fmt.Println("Specify the bootstrap key using --key=<KEY>.")
        cmd.Usage()
        os.Exit(1)
    }

    if cmd.Flags().Changed("super-users") {
        req.SuperUserEmails = strings.Split(bootstrapSuperUserEmails, ",")
    } else {
        fmt.Println("Specify at least one email to use for super users using --super-user-email.")
        cmd.Usage()
        os.Exit(1)
    }

    req.SuperRoleName = bootstrapSuperRoleName
    _, err := client.Bootstrap(context.Background(), req)
    if err != nil {
        return err
    }
    printIf(! quiet, "OK\n")
    return nil
}
