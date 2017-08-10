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
                Field: "id",
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
                Field: "name",
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

    marker := "fake-uuid"

    qs := "SELECT o.id, o.name FROM orders AS o WHERE "
    opts := &pb.SearchOptions{
        SortFields: []*pb.SortField{
            &pb.SortField{
                Field: "id",
                Direction: pb.SortDirection_ASC,
            },
        },
        Marker: marker,
    }
    qargs := make([]interface{}, 0)

    AddMarkerWhere(&qs, opts, "o", false, &qargs)
    expect := `SELECT o.id, o.name FROM orders AS o WHERE o.uuid > ?`
    assert.Equal(expect, qs)
    expectQargs := make([]interface{}, 1)
    expectQargs[0] = marker
    assert.Equal(expectQargs, qargs)

    // Verify that if the sort order is DESC, that the operator changes from >=
    // to <
    qs = "SELECT o.id, o.name FROM orders AS o WHERE "
    opts = &pb.SearchOptions{
        SortFields: []*pb.SortField{
            &pb.SortField{
                Field: "id",
                Direction: pb.SortDirection_DESC,
            },
        },
        Marker: marker,
    }
    qargs = make([]interface{}, 0)

    AddMarkerWhere(&qs, opts, "o", false, &qargs)
    expect = `SELECT o.id, o.name FROM orders AS o WHERE o.uuid < ?`
    assert.Equal(expect, qs)
    expectQargs = make([]interface{}, 1)
    expectQargs[0] = marker
    assert.Equal(expectQargs, qargs)

    // Verify that the includeAnd parameter adds a formatted '\nAND ' to the
    // query string
    qs = "SELECT o.id, o.name FROM orders AS o WHERE o.name LIKE ?"
    opts = &pb.SearchOptions{
        SortFields: []*pb.SortField{
            &pb.SortField{
                Field: "id",
                Direction: pb.SortDirection_DESC,
            },
        },
        Marker: marker,
    }
    qargs = make([]interface{}, 0)

    AddMarkerWhere(&qs, opts, "o", true, &qargs)
    expect = `SELECT o.id, o.name FROM orders AS o WHERE o.name LIKE ?
AND o.uuid < ?`
    assert.Equal(expect, qs)
    expectQargs = make([]interface{}, 1)
    expectQargs[0] = marker
    assert.Equal(expectQargs, qargs)
}

func TestNormalizeSortFields(t *testing.T) {
    assert := assert.New(t)

    validSortFields := []string{
        "uuid",
        "email",
        "name",
        "display name",
        "display_name",
    }
    sortFieldAliases := map[string]string{
        "name": "display_name",
        "display name": "display_name",
        "display_name": "display_name",
    }

    // Test with a non-aliased field for sorting
    opts := &pb.SearchOptions{
        SortFields: []*pb.SortField{
            &pb.SortField{
                Field: "uuid",
                Direction: pb.SortDirection_ASC,
            },
        },
    }

    err := NormalizeSortFields(opts, &validSortFields, &sortFieldAliases)
    assert.Nil(err)

    // Test with an aliased field for sorting and check that the Field has been
    // updated to the underlying correct field name
    opts = &pb.SearchOptions{
        SortFields: []*pb.SortField{
            &pb.SortField{
                Field: "name",
                Direction: pb.SortDirection_ASC,
            },
        },
    }

    err = NormalizeSortFields(opts, &validSortFields, &sortFieldAliases)
    assert.Nil(err)

    assert.Equal("display_name", opts.SortFields[0].Field)

    // Test that an invalid sort field results in an error
    opts = &pb.SearchOptions{
        SortFields: []*pb.SortField{
            &pb.SortField{
                Field: "unknown",
                Direction: pb.SortDirection_ASC,
            },
        },
    }

    err = NormalizeSortFields(opts, &validSortFields, &sortFieldAliases)
    assert.NotNil(err)
}
