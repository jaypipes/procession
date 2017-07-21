package errors

import "google.golang.org/grpc/status"
import "google.golang.org/grpc/codes"

var (
    FORBIDDEN = status.Error(
        codes.PermissionDenied,
        "User is not authorized to perform that action",
    )
)
