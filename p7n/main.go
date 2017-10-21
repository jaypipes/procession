package main

import (
	"fmt"
	"os"

	"github.com/jaypipes/procession/p7n/commands"
)

func main() {
	err := commands.RootCommand.Execute()
	if err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}
