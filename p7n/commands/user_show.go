package commands

import (
    "fmt"
    "golang.org/x/net/context"

    "github.com/spf13/cobra"
    pb "github.com/jaypipes/procession/proto"
)

var (
    showUserUuid string
    showUserDisplayName string
    showUserEmail string
    showUserSlug string
)

var userShowCommand = &cobra.Command{
    Use: "show ",
    Short: "Show information for a single user",
    RunE: showUser,
}

func addUserShowFlags() {
    userShowCommand.Flags().StringVarP(
        &showUserUuid,
        "uuid", "u",
        unsetSentinel,
        "UUID for the user to show.",
    )
    userShowCommand.Flags().StringVarP(
        &showUserDisplayName,
        "display-name", "n",
        unsetSentinel,
        "Display name for the user to show.",
    )
    userShowCommand.Flags().StringVarP(
        &showUserEmail,
        "email", "",
        unsetSentinel,
        "Email for the user to show.",
    )
    userShowCommand.Flags().StringVarP(
        &showUserSlug,
        "slug", "",
        unsetSentinel,
        "Slug for the user to show.",
    )
}

func init() {
    addUserShowFlags()
}

func showUser(cmd *cobra.Command, args []string) error {
    searchFields := &pb.GetUserFields{}
    valid := false
    if isSet(showUserUuid) {
        searchFields.Uuid = &pb.StringValue{Value: showUserUuid}
        valid = true
    }
    if isSet(showUserDisplayName) {
        searchFields.DisplayName = &pb.StringValue{Value: showUserDisplayName}
        valid = true
    }
    if isSet(showUserEmail) {
        searchFields.Email = &pb.StringValue{Value: showUserEmail}
        valid = true
    }
    if isSet(showUserSlug) {
        searchFields.Slug = &pb.StringValue{Value: showUserSlug}
        valid = true
    }
    if ! valid {
        fmt.Println("Please specify at least one email, UUID, slug or display name")
        cmd.Usage()
        return nil
    }
    conn, err := connect()
    if err != nil {
        return err
    }
    defer conn.Close()

    client := pb.NewIAMClient(conn)
    req := &pb.GetUserRequest{
        Session: nil,
        SearchFields: searchFields,
    }
    user, err := client.GetUser(context.Background(), req)
    if err != nil {
        return err
    }
    if user.Uuid == "" {
        fmt.Printf("No user found matching request\n")
        return nil
    }
    fmt.Printf("UUID:         %s\n", user.Uuid)
    fmt.Printf("Display name: %s\n", user.DisplayName)
    fmt.Printf("Email:        %s\n", user.Email)
    return nil
}
