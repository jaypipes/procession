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
    orgCommand.AddCommand(orgSetCommand)
    orgCommand.AddCommand(orgMembersCommand)
}
