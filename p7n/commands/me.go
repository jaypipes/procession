package commands

import (
	"fmt"
	"golang.org/x/net/context"

	pb "github.com/jaypipes/procession/proto"
	"github.com/spf13/cobra"
)

var meCommand = &cobra.Command{
	Use:   "me",
	Short: "Shows information about the context that will be used to execute a command",
	RunE:  runMe,
}

func init() {
}

func runMe(cmd *cobra.Command, args []string) error {
	checkAuthUser(cmd)
	conn := connect()
	defer conn.Close()

	client := pb.NewIAMClient(conn)
	req := &pb.UserGetRequest{
		Session: &pb.Session{User: authUser},
		Search:  authUser,
	}
	user, err := client.UserGet(context.Background(), req)
	if err != nil {
		return err
	}
	if user.Uuid == "" {
		fmt.Println("Error: unknown or invalid user information.")
		return nil
	}
	fmt.Println("OK")
	return nil
}
