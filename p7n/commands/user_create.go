package commands

import (
    "fmt"
    "os"
    "strings"

    "golang.org/x/net/context"

    "github.com/spf13/cobra"
    pb "github.com/jaypipes/procession/proto"
)

var (
    userCreateDisplayName string
    userCreateEmail string
    userCreateRoles string
)

var userCreateCommand = &cobra.Command{
    Use: "create",
    Short: "Creates a new user",
    Run: userCreate,
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
    userCreateCommand.Flags().StringVarP(
        &userCreateRoles,
        "roles", "",
        "",
        "Comma-separated list of roles to add the user to." +
        rolesHelpExtended,
    )
}

func init() {
    setupUserCreateFlags()
}

func userCreate(cmd *cobra.Command, args []string) {
    checkAuthUser(cmd)
    conn := connect()
    defer conn.Close()

    client := pb.NewIAMClient(conn)
    req := &pb.UserSetRequest{
        Session: &pb.Session{User: authUser},
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
    if cmd.Flags().Changed("roles") {
        req.Changed.Roles = strings.Split(userCreateRoles, ",")
    }
    resp, err := client.UserSet(context.Background(), req)
    exitIfError(err)
    user := resp.User
    if quiet {
        fmt.Println(user.Uuid)
    } else {
        fmt.Printf("Successfully created user with UUID %s\n", user.Uuid)
    }
    if verbose {
        fmt.Printf("UUID:         %s\n", user.Uuid)
        fmt.Printf("Display name: %s\n", user.DisplayName)
        fmt.Printf("Email:        %s\n", user.Email)
        fmt.Printf("Slug:         %s\n", user.Slug)
        if len(user.Roles) == 0 {
            fmt.Println("Roles:        None")
        } else {
            roleStrs := make([]string, len(user.Roles))
            for x, role := range user.Roles {
                orgStr := ""
                if role.Organization != nil {
                    orgStr = fmt.Sprintf(" (%s)", role.Organization.DisplayName)
                }
                tmp := fmt.Sprintf("%s%s", role.DisplayName, orgStr)
                roleStrs[x] = tmp
            }
            roleStr := strings.Join(roleStrs, ", ")
            fmt.Printf("Roles:        %s\n", roleStr)
        }
    }
}
