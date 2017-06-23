package commands

import (
    "fmt"
    "os"
    "golang.org/x/net/context"

    "github.com/spf13/cobra"
    pb "github.com/jaypipes/procession/proto"
)

var (
    userCreateDisplayName string
    userCreateEmail string
)

var userCreateCommand = &cobra.Command{
    Use: "create",
    Short: "Creates a new user",
    RunE: userCreate,
}

func setupUserCreateFlags() {
    userCreateCommand.Flags().StringVarP(
        &userCreateDisplayName,
        "display-name", "n",
        "",
        "Display name for the user.",
    )
    userCreateCommand.Flags().StringVarP(
        &userCreateEmail,
        "email", "e",
        "",
        "Email for the user.",
    )
}

func init() {
    setupUserCreateFlags()
}

func userCreate(cmd *cobra.Command, args []string) error {
    checkAuthUser(cmd)
    conn := connect()
    defer conn.Close()

    client := pb.NewIAMClient(conn)
    req := &pb.UserSetRequest{
        Session: nil,
        Changed: &pb.UserSetFields{},
    }

    if cmd.Flags().Changed("display-name") {
        req.Changed.DisplayName = &pb.StringValue{
            Value: userCreateDisplayName,
        }
    } else {
        fmt.Println("Specify a display name using --display-name=<NAME>.")
        cmd.Usage()
        os.Exit(1)
    }
    if cmd.Flags().Changed("email") {
        req.Changed.Email = &pb.StringValue{
            Value: userCreateEmail,
        }
    } else {
        fmt.Println("Specify an email using --email=<EMAIL>.")
        cmd.Usage()
        os.Exit(1)
    }
    resp, err := client.UserSet(context.Background(), req)
    if err != nil {
        return err
    }
    user := resp.User
    if quiet {
        fmt.Println(user.Uuid)
    } else {
        fmt.Printf("Successfully created user with UUID %s\n", user.Uuid)
        fmt.Printf("UUID:         %s\n", user.Uuid)
        fmt.Printf("Display name: %s\n", user.DisplayName)
        fmt.Printf("Email:        %s\n", user.Email)
        fmt.Printf("Slug:         %s\n", user.Slug)
    }
    return nil
}
