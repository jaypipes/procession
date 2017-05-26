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
    userCommand.AddCommand(userGetCommand)
    userCommand.AddCommand(userSetCommand)
    userCommand.AddCommand(userDeleteCommand)
    userCommand.AddCommand(userMembersCommand)
}
