package commands

import (
    "github.com/spf13/cobra"
)

var RootCommand = &cobra.Command{
    Use: "p7n",
    Short: "p7n - the Procession CLI tool.",
    Long: "Manipulate a Procession code review system.",
}

func init() {
    RootCommand.AddCommand(userCommand)
    RootCommand.SilenceUsage = true
}
