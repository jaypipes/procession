package commands

import (
    "github.com/spf13/cobra"
)

var userCommand = &cobra.Command{
    Use: "user",
    Short: "Manipulate user information",
}

func init() {
    userCommand.AddCommand(userListCommand)
    userCommand.AddCommand(userShowCommand)
    userCommand.AddCommand(userSetCommand)
}
