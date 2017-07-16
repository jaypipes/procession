package commands

import (
    "fmt"
    "os"

    "golang.org/x/net/context"

    "github.com/spf13/cobra"
    pb "github.com/jaypipes/procession/proto"
)

var (
    bootstrapKey string
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
    _, err := client.Bootstrap(context.Background(), req)
    if err != nil {
        return err
    }
    printIf(! quiet, "OK\n")
    return nil
}
