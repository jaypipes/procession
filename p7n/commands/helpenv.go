package commands

import (
	"os"
	"strconv"

	"github.com/olekukonko/tablewriter"
	"github.com/spf13/cobra"
)

var helpEnvCommand = &cobra.Command{
	Use:   "helpenv",
	Short: "Show environment variable help",
	Long: `Shows a table of information about environment variables, the
    associated CLI option, and the currently evaluated value of that variable
    that can be used to influence p7n's behaviour.`,
	Run: showEnvHelp,
}

func showEnvHelp(cmd *cobra.Command, args []string) {
	headers := []string{
		"Env Name",
		"CLI Option",
		"Value",
	}
	rows := [][]string{
		[]string{
			"PROCESSION_HOST",
			"--host",
			connectHost,
		},
		[]string{
			"PROCESSION_PORT",
			"--port",
			strconv.Itoa(connectPort),
		},
		[]string{
			"PROCESSION_USER",
			"--user",
			authUser,
		},
	}
	table := tablewriter.NewWriter(os.Stdout)
	table.SetHeader(headers)
	table.AppendBulk(rows)
	table.Render()
	return
}
