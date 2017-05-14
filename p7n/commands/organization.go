package commands

import (
    "github.com/spf13/cobra"
)

var organizationCommand = &cobra.Command{
    Use: "organization",
    Short: "Manipulate organization information",
}

func init() {
    organizationCommand.AddCommand(organizationListCommand)
    organizationCommand.AddCommand(organizationGetCommand)
    organizationCommand.AddCommand(organizationSetCommand)
}
