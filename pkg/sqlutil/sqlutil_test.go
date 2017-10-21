package sqlutil

import (
	"testing"

	"github.com/stretchr/testify/assert"

	pb "github.com/jaypipes/procession/proto"
)

func TestInParamString(t *testing.T) {
	assert := assert.New(t)

	assert.Equal("IN (?)", InParamString(1))
	assert.Equal("IN (?, ?)", InParamString(2))
	assert.Equal("IN (?, ?, ?)", InParamString(3))
}

func TestAddOrderBy(t *testing.T) {
	assert := assert.New(t)

	qs := "SELECT o.id, o.name FROM orders AS o"
	opts := &pb.SearchOptions{
		SortFields: []*pb.SortField{
			&pb.SortField{
				Field:     "id",
				Direction: pb.SortDirection_ASC,
			},
		},
	}

	AddOrderBy(&qs, opts, "o")
	expect := `SELECT o.id, o.name FROM orders AS o
ORDER BY o.id ASC`
	assert.Equal(expect, qs)

	qs = "SELECT o.id, o.name FROM orders AS o"
	opts = &pb.SearchOptions{
		SortFields: []*pb.SortField{
			&pb.SortField{
				Field:     "name",
				Direction: pb.SortDirection_DESC,
			},
		},
	}

	AddOrderBy(&qs, opts, "o")
	expect = `SELECT o.id, o.name FROM orders AS o
ORDER BY o.name DESC`
	assert.Equal(expect, qs)
}

func TestAddMarkerWhere(t *testing.T) {
	assert := assert.New(t)

	infos := []*SortFieldInfo{
		&SortFieldInfo{
			Name:   "id",
			Unique: true,
		},
		&SortFieldInfo{
			Name:   "name",
			Unique: false,
			Aliases: []string{
				"display_name",
				"display name",
			},
		},
		&SortFieldInfo{
			Name:   "uuid",
			Unique: true,
		},
	}
	markerUuid := "fake-uuid"
	sortFieldValue := "sort field value"
	lookup := func() string {
		return sortFieldValue
	}

	qs := "SELECT o.id, o.name FROM orders AS o WHERE "
	opts := &pb.SearchOptions{
		SortFields: []*pb.SortField{
			&pb.SortField{
				Field:     "id",
				Direction: pb.SortDirection_ASC,
			},
		},
		Marker: markerUuid,
	}
	qargs := make([]interface{}, 0)

	AddMarkerWhere(&qs, opts, "o", false, &qargs, infos, lookup)
	expect := `SELECT o.id, o.name FROM orders AS o WHERE o.id > ?`
	assert.Equal(expect, qs)
	expectQargs := make([]interface{}, 1)
	expectQargs[0] = sortFieldValue
	assert.Equal(expectQargs, qargs)

	// Verify that if the sort order is DESC, that the operator changes from >
	// to <
	qs = "SELECT o.id, o.name FROM orders AS o WHERE "
	opts = &pb.SearchOptions{
		SortFields: []*pb.SortField{
			&pb.SortField{
				Field:     "id",
				Direction: pb.SortDirection_DESC,
			},
		},
		Marker: markerUuid,
	}
	qargs = make([]interface{}, 0)

	AddMarkerWhere(&qs, opts, "o", false, &qargs, infos, lookup)
	expect = `SELECT o.id, o.name FROM orders AS o WHERE o.id < ?`
	assert.Equal(expect, qs)
	expectQargs = make([]interface{}, 1)
	expectQargs[0] = sortFieldValue
	assert.Equal(expectQargs, qargs)

	// Verify that the includeAnd parameter adds a formatted '\nAND ' to the
	// query string
	qs = "SELECT o.id, o.name FROM orders AS o WHERE o.name LIKE ?"
	opts = &pb.SearchOptions{
		SortFields: []*pb.SortField{
			&pb.SortField{
				Field:     "id",
				Direction: pb.SortDirection_DESC,
			},
		},
		Marker: markerUuid,
	}
	qargs = make([]interface{}, 0)

	AddMarkerWhere(&qs, opts, "o", true, &qargs, infos, lookup)
	expect = `SELECT o.id, o.name FROM orders AS o WHERE o.name LIKE ?
AND o.id < ?`
	assert.Equal(expect, qs)
	expectQargs = make([]interface{}, 1)
	expectQargs[0] = sortFieldValue
	assert.Equal(expectQargs, qargs)

	// Verify that if the sort field is not unique, that we use a greater than
	// or equal on the non-unique sort field and we add the tiebreaker
	// condition on uuid value
	qs = "SELECT o.id, o.name FROM orders AS o WHERE "
	opts = &pb.SearchOptions{
		SortFields: []*pb.SortField{
			&pb.SortField{
				Field:     "name",
				Direction: pb.SortDirection_ASC,
			},
		},
		Marker: markerUuid,
	}
	qargs = make([]interface{}, 0)

	AddMarkerWhere(&qs, opts, "o", false, &qargs, infos, lookup)
	expect = "SELECT o.id, o.name FROM orders AS o WHERE o.name >= ?\nAND o.uuid > ?"
	assert.Equal(expect, qs)
	expectQargs = make([]interface{}, 2)
	expectQargs[0] = sortFieldValue
	expectQargs[1] = markerUuid
	assert.Equal(expectQargs, qargs)
}

func TestNormalizeSortFields(t *testing.T) {
	assert := assert.New(t)

	sortFieldInfos := []*SortFieldInfo{
		&SortFieldInfo{
			Name:   "uuid",
			Unique: true,
		},
		&SortFieldInfo{
			Name:   "email",
			Unique: true,
		},
		&SortFieldInfo{
			Name:   "display_name",
			Unique: false,
			Aliases: []string{
				"name",
				"display name",
				"display_name",
			},
		},
	}

	// Test with a non-aliased field for sorting
	opts := &pb.SearchOptions{
		SortFields: []*pb.SortField{
			&pb.SortField{
				Field:     "uuid",
				Direction: pb.SortDirection_ASC,
			},
		},
	}

	err := NormalizeSortFields(opts, &sortFieldInfos)
	assert.Nil(err)

	// Test with an aliased field for sorting and check that the Field has been
	// updated to the underlying correct field name
	opts = &pb.SearchOptions{
		SortFields: []*pb.SortField{
			&pb.SortField{
				Field:     "name",
				Direction: pb.SortDirection_ASC,
			},
		},
	}

	err = NormalizeSortFields(opts, &sortFieldInfos)
	assert.Nil(err)

	assert.Equal("display_name", opts.SortFields[0].Field)

	// Test that an invalid sort field results in an error
	opts = &pb.SearchOptions{
		SortFields: []*pb.SortField{
			&pb.SortField{
				Field:     "unknown",
				Direction: pb.SortDirection_ASC,
			},
		},
	}

	err = NormalizeSortFields(opts, &sortFieldInfos)
	assert.NotNil(err)
}
