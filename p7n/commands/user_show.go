package commands

import (
    "fmt"

    "github.com/spf13/cobra"
)

var userShowCommand = &cobra.Command{
    Use: "show",
    Short: "Show information for a user",
    Run: showUser,
}

func showUser(cmd *cobra.Command, args []string) {
    if len(args) != 1 {
        fmt.Println("Please specify an email, user UUID, or display name")
        cmd.Usage()
        return
    }
    fmt.Printf("Show user %v\n", args)
}
