package commands

import (
    "fmt"
    "os"
    "golang.org/x/net/context"

    "github.com/spf13/cobra"
    pb "github.com/jaypipes/procession/proto"
)

var (
    userUpdateDisplayName string
    userUpdateEmail string
)

var userUpdateCommand = &cobra.Command{
    Use: "update <identifier>",
    Short: "Updates information for a user",
    Run: userUpdate,
}

func setupUserUpdateFlags() {
    userUpdateCommand.Flags().StringVarP(
        &userUpdateDisplayName,
        "display-name", "n",
        "",
        "Display name for the user.",
    )
    userUpdateCommand.Flags().StringVarP(
        &userUpdateEmail,
        "email", "e",
        "",
        "Email for the user.",
    )
}

func init() {
    setupUserUpdateFlags()
}

func userUpdate(cmd *cobra.Command, args []string) {
    checkAuthUser(cmd)
    conn := connect()
    defer conn.Close()

    client := pb.NewIAMClient(conn)
    req := &pb.UserSetRequest{
        Session: nil,
        Changed: &pb.UserSetFields{},
    }

    if len(args) != 1 {
        fmt.Println("Please specify a user identifier.")
        cmd.Usage()
        os.Exit(1)
    } else {
        req.Search = &pb.StringValue{Value: args[0]}
    }

    if cmd.Flags().Changed("display-name") {
        req.Changed.DisplayName = &pb.StringValue{
            Value: userUpdateDisplayName,
        }
    }
    if cmd.Flags().Changed("email") {
        req.Changed.Email = &pb.StringValue{
            Value: userUpdateEmail,
        }
    }
    resp, err := client.UserSet(context.Background(), req)
    exitIfError(err)
    user := resp.User
    printIf(! quiet || verbose, "OK\n")
    printIf(verbose, "Successfully saved user <%s>\n", user.Uuid)
    printIf(verbose, "UUID:         %s\n", user.Uuid)
    printIf(verbose, "Display name: %s\n", user.DisplayName)
    printIf(verbose, "Email:        %s\n", user.Email)
    printIf(verbose, "Slug:         %s\n", user.Slug)
}
