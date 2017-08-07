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
