package util

import (
    "strings"
    "regexp"
    "encoding/hex"

    "github.com/pborman/uuid"
)

const (
    reUuidStr = "^[a-f0-9]{32}$"
)

var (
    RegexUuid = regexp.MustCompilePOSIX(reUuidStr)
)

// Returns whether a subject string looks like a UUID
func IsUuidLike(subject string) bool {
    return RegexUuid.MatchString(UuidFormatDb(subject))
}

// Given a string, removes whitespace, hyphens and lowercases the string,
// making it ready for insertion or querying in the DB
func UuidFormatDb(subject string) string {
    return strings.ToLower(
        strings.Replace(
            strings.TrimSpace(subject),
            "-", "", 4,
        ),
    )
}

// Returns whether a subject string looks like an email
func IsEmailLike(subject string) bool {
    if strings.IndexByte(subject, '@') < 1 {
        return false
    }
    if strings.ContainsAny(subject, " \n\r\t\b") {
        return false
    }
    return true
}

// Returns a new "ordered" UUID as 32 alphanumeric characters with no dashes --
// the most efficient string representation for storage in a DB (besides
// storing as BINARY, which makes querying ugly and overly difficult for little
// benefit)
// 
// Returns a UUID type 1 value, with the more constant segments of the
// UUID at the start of the UUID. This allows us to have mostly monotonically
// increasing UUID values, which are much better for INSERT/UPDATE performance
// in the DB.
//
// A UUID1 hex looks like:
//
// '27392da28bae11e4961de06995034837'
//
// From this, we need to take the last two segments, which represent the more
// constant information about the node we're on, and place those first in the
// new UUID's bytes. We then take the '11e4' segment, which represents the
// most significant bits of the timestamp part of the UUID, prefixed with a
// '1' for UUID type, and place that next, followed by the second segment and
// finally the first segment, which are the next most significant bits of the
// timestamp 60-bit number embedded in the UUID.
//
// So, we convert the above hex to this instead:
//
// '961de0699503483711e48bae27392da2'
//
func OrderedUuid() (string) {
    u := uuid.NewUUID()

    var o [16]byte
    var y [32]byte

    copy(o[0:], u[8:])
    copy(o[8:], u[6:8])
    copy(o[10:], u[4:6])
    copy(o[12:], u[0:4])

    hex.Encode(y[:], o[:])
    return string(y[:])
}
