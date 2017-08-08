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
