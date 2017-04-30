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
    conn, err := connect()
    if err != nil {
        fmt.Printf("There was a problem connecting to the Procession server: %v\n", err)
        return
    }
    defer conn.Close()
    fmt.Printf("Show user %v\n", args)
}
