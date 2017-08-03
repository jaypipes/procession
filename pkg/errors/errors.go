package errors

import "google.golang.org/grpc/status"
import "google.golang.org/grpc/codes"

var (
    FORBIDDEN = status.Error(
        codes.PermissionDenied,
        "User is not authorized to perform that action",
    )
    INVALID_PUBLIC_CHILD_PRIVATE_PARENT = status.Error(
        codes.InvalidArgument,
        "Cannot make a child organization public if its parent is private.",
    )
)

func NOTFOUND(objType string, identifier string) error {
    return status.Errorf(
        codes.NotFound,
        "No such %s '%s'",
        objType,
        identifier,
    )
}

func DUPLICATE(field string, identifier string) error {
    return status.Errorf(
        codes.AlreadyExists,
        "Duplicate %s '%s'",
        field,
        identifier,
    )
}

func TOO_MANY_MATCHES(search string) error {
    return status.Errorf(
        codes.InvalidArgument,
        `Multiple records found when searching for '%s'.

Use a more specific search (e.g. try listing records and get'ing by UUID).`,
        search,
    )
}

func IsNotFound(err error) bool {
    if s, ok := status.FromError(err); ok {
        if s.Code() == codes.NotFound {
            return true
        }
    }
    return false
}
