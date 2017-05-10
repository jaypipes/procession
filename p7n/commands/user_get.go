package commands

import (
    "fmt"
    "golang.org/x/net/context"

    "github.com/spf13/cobra"
    pb "github.com/jaypipes/procession/proto"
)

var (
    getUserUuid string
    getUserDisplayName string
    getUserEmail string
    getUserSlug string
)

var userGetCommand = &cobra.Command{
    Use: "get ",
    Short: "Get information for a single user",
    RunE: getUser,
}

func addUserGetFlags() {
    userGetCommand.Flags().StringVarP(
        &getUserUuid,
        "uuid", "u",
        unsetSentinel,
        "UUID for the user to get.",
    )
    userGetCommand.Flags().StringVarP(
        &getUserDisplayName,
        "display-name", "n",
        unsetSentinel,
        "Display name for the user to get.",
    )
    userGetCommand.Flags().StringVarP(
        &getUserEmail,
        "email", "",
        unsetSentinel,
        "Email for the user to get.",
    )
    userGetCommand.Flags().StringVarP(
        &getUserSlug,
        "slug", "",
        unsetSentinel,
        "Slug for the user to get.",
    )
}

func init() {
    addUserGetFlags()
}

func getUser(cmd *cobra.Command, args []string) error {
    searchFields := &pb.GetUserFields{}
    valid := false
    if isSet(getUserUuid) {
        searchFields.Uuid = &pb.StringValue{Value: getUserUuid}
        valid = true
    }
    if isSet(getUserDisplayName) {
        searchFields.DisplayName = &pb.StringValue{Value: getUserDisplayName}
        valid = true
    }
    if isSet(getUserEmail) {
        searchFields.Email = &pb.StringValue{Value: getUserEmail}
        valid = true
    }
    if isSet(getUserSlug) {
        searchFields.Slug = &pb.StringValue{Value: getUserSlug}
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
    fmt.Printf("Slug:         %s\n", user.Slug)
    return nil
}
