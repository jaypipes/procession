package commands

import (
    "github.com/spf13/cobra"
)

var orgCommand = &cobra.Command{
    Use: "organization",
    Short: "Manipulate organization information",
}

func init() {
    orgCommand.AddCommand(orgListCommand)
    orgCommand.AddCommand(orgGetCommand)
    orgCommand.AddCommand(orgCreateCommand)
    orgCommand.AddCommand(orgUpdateCommand)
    orgCommand.AddCommand(orgDeleteCommand)
    orgCommand.AddCommand(orgMembersCommand)
}
