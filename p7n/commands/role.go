package commands

import (
	"github.com/spf13/cobra"
)

var roleCommand = &cobra.Command{
	Use:   "role",
	Short: "Manipulate role information",
}

func init() {
	roleCommand.AddCommand(roleGetCommand)
	roleCommand.AddCommand(roleCreateCommand)
	roleCommand.AddCommand(roleUpdateCommand)
	roleCommand.AddCommand(roleDeleteCommand)
	roleCommand.AddCommand(roleListCommand)
}
