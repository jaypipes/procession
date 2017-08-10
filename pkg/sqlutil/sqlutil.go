package sqlutil

import (
    "fmt"
    "strings"

    "github.com/go-sql-driver/mysql"

    "github.com/jaypipes/procession/pkg/errors"
    pb "github.com/jaypipes/procession/proto"
)

// Returns a string containing the expression IN with one or more question
// marks for parameter interpolation. If numArgs argument is 3, the returned
// value would be "IN (?, ?, ?)"
func InParamString(numArgs int) string {
    resLen := 5 + ((numArgs * 3) - 2)
    res := make([]byte, resLen)
    res[0] = 'I'
    res[1] = 'N'
    res[2] = ' '
    res[3] = '('
    for x := 4; x < (resLen - 1); x++ {
        res[x] = '?'
        x++
        if x < (resLen - 1) {
            res[x] = ','
            x++
            res[x] = ' '
        }
    }
    res[resLen - 1] = ')'
    return string(res)
}

// Returns true if the supplied error represents a duplicate key error
func IsDuplicateKey(err error) bool {
    if err == nil {
        return false
    }
    me, ok := err.(*mysql.MySQLError)
    if ! ok {
        // TODO(jaypipes): Handle PostgreSQLisms here
        return false
    }
    if me.Number == 1062 {
        return true
    }
    return false
}

// Returns true if the supplied error is a duplicate key error and the supplied
// constraint name is the one that was violated
func IsDuplicateKeyOn(err error, constraintName string) bool {
    if err == nil {
        return false
    }
    me, ok := err.(*mysql.MySQLError)
    if ! ok {
        // TODO(jaypipes): Handle PostgreSQLisms here
        return false
    }
    return strings.Contains(me.Error(), constraintName)
}

// Extends the supplied raw SQL string with an ORDER BY clause based on a
// pb.SearchOptions message and a table alias
func AddOrderBy(qs *string, opts *pb.SearchOptions, alias string) {
    *qs = *qs + "\nORDER BY "
    for x, sortField := range opts.SortFields {
        comma := ""
        if x > 0 {
            comma = ","
        }
        aliasStr := alias
        if alias != "" && ! strings.Contains(alias, ".") {
            aliasStr = aliasStr + "."
        }
        *qs = *qs + fmt.Sprintf(
            "%s%s%s %s",
            comma,
            aliasStr,
            sortField.Field,
            sortField.Direction,
        )
    }
}

// Examines the supplied search options and injects a WHERE clause that filters
// a page of results based on a marker value and the sort direction requested.
// The DB field we winnow is always the uuid field (which is what the marker
// contains.
func AddMarkerWhere(
    qs *string,
    opts *pb.SearchOptions,
    alias string,
    includeAnd bool,
    qargs *[]interface{},
) {
    // Note that sort fields should already be normalized before calling this
    // function
    if len(opts.SortFields) > 0 && opts.Marker != "" {
        sortField := opts.SortFields[0]
        aliasStr := alias
        if alias != "" && ! strings.Contains(alias, ".") {
            aliasStr = aliasStr + "."
        }
        operator := ">"
        if sortField.Direction == pb.SortDirection_DESC {
            operator = "<"
        }
        andStr := ""
        if includeAnd {
            andStr = "\nAND "
        }
        *qs = *qs + fmt.Sprintf(
            "%s%suuid %s ?",
            andStr,
            aliasStr,
            operator,
        )
        *qargs = append(*qargs, opts.Marker)
    }
}

// Looks through any requested sort fields and validates that the sort field is
// something we can sort on, replacing any aliases with the correct database
// field name. Returns an error if any requested sort field isn't valid.
func NormalizeSortFields(
    opts *pb.SearchOptions,
    validFields *[]string,
    aliases *map[string]string,
) error {
    newSortFields := make([]*pb.SortField, 0)
    for _, sortField := range opts.SortFields {
        fname := strings.ToLower(sortField.Field)
        found := false
        for _, val := range *validFields {
            if val == fname {
                found = true
                break
            }
        }
        if ! found {
            return errors.INVALID_SORT_FIELD(fname)
        }
        normalName, aliased := (*aliases)[fname]
        if ! aliased {
            normalName = fname
        }
        newSortField := &pb.SortField{
            Field: normalName,
            Direction: sortField.Direction,
        }
        newSortFields = append(newSortFields, newSortField)
    }
    opts.SortFields = newSortFields
    return nil
}
