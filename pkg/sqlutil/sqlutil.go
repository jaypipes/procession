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
	res[resLen-1] = ')'
	return string(res)
}

// Returns true if the supplied error represents a duplicate key error
func IsDuplicateKey(err error) bool {
	if err == nil {
		return false
	}
	me, ok := err.(*mysql.MySQLError)
	if !ok {
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
	if !ok {
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
		if alias != "" && !strings.Contains(alias, ".") {
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
	infos []*SortFieldInfo,
	markerLookup func() string,
) {
	// Note that sort fields should already be normalized before calling this
	// function
	if len(opts.SortFields) > 0 && opts.Marker != "" {
		sortField := opts.SortFields[0]
		info := findSortFieldInfo(sortField, infos)
		if info == nil {
			return
		}
		aliasStr := alias
		if alias != "" && !strings.Contains(alias, ".") {
			aliasStr = aliasStr + "."
		}
		operator := ">"
		if sortField.Direction == pb.SortDirection_DESC {
			operator = "<"
		}
		tiebreakerCond := ""
		markerUuid := opts.Marker
		if sortField.Field != "uuid" {
			// Look up the marker record's sort field value
			markerSortFieldValue := markerLookup()
			*qargs = append(*qargs, markerSortFieldValue)
			if !info.Unique {
				// For sorts on non-unique fields, we need to include a
				// tie-breaking conditional on a unique column (uuid)
				tiebreakerCond = fmt.Sprintf(
					"\nAND %suuid %s ?",
					aliasStr,
					operator,
				)
				*qargs = append(*qargs, markerUuid)
				// The primary WHERE condition is on a non-unique field and so
				// add an = to deal with ties on the sort field. The tiebreaker
				// condition on the uuid column above needs to be without the
				// equality operator.
				operator = operator + "="
			}
			// If we're sorting by
		} else {
			*qargs = append(*qargs, markerUuid)
		}
		andStr := ""
		if includeAnd {
			andStr = "\nAND "
		}
		*qs = *qs + fmt.Sprintf(
			"%s%s%s %s ?%s",
			andStr,
			aliasStr,
			sortField.Field,
			operator,
			tiebreakerCond,
		)
	}
}

func findSortFieldInfo(sortField *pb.SortField, infos []*SortFieldInfo) *SortFieldInfo {
	for _, info := range infos {
		if sortField.Field == info.Name {
			return info
		}
	}
	return nil
}

type SortFieldInfo struct {
	Name    string
	Unique  bool
	Aliases []string
}

// Looks through any requested sort fields and validates that the sort field is
// something we can sort on, replacing any aliases with the correct database
// field name. Returns an error if any requested sort field isn't valid.
func NormalizeSortFields(
	opts *pb.SearchOptions,
	sortFieldInfos *[]*SortFieldInfo,
) error {
	newSortFields := make([]*pb.SortField, 0)
	for _, sortField := range opts.SortFields {
		var sortFieldInfo *SortFieldInfo
		fname := strings.ToLower(sortField.Field)
		found := false
		for _, sortFieldInfo = range *sortFieldInfos {
			if sortFieldInfo.Name == fname {
				found = true
				break
			}
			if len(sortFieldInfo.Aliases) > 0 {
				for _, alias := range sortFieldInfo.Aliases {
					if alias == fname {
						found = true
						break
					}
				}
				if found {
					break
				}
			}
		}
		if !found {
			return errors.INVALID_SORT_FIELD(fname)
		}
		newSortField := &pb.SortField{
			Field:     sortFieldInfo.Name,
			Direction: sortField.Direction,
		}
		newSortFields = append(newSortFields, newSortField)
	}
	opts.SortFields = newSortFields
	return nil
}
