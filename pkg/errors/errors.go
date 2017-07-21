package errors

import "google.golang.org/grpc/status"
import "google.golang.org/grpc/codes"

var (
    FORBIDDEN = status.Error(
        codes.PermissionDenied,
        "User is not authorized to perform that action",
    )
)

func NOTFOUND(objType string, identifier string) error {
    return status.Errorf(
        codes.NotFound,
        "No such %s %s",
        objType,
        identifier,
    )
}
