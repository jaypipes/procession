package storage

import (
    "errors"
)

var (
    ERR_CONCURRENT_UPDATE = errors.New("Another thread updated this record concurrently. Please try your update again after refreshing your view of it.")
    ERR_NOTFOUND_USER = errors.New("No such user")
)
