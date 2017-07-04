package sqlutil

import (
    "testing"

    "github.com/stretchr/testify/assert"
)

func TestInParamString(t *testing.T) {
    assert := assert.New(t)

    assert.Equal("IN (?)", InParamString(1))
    assert.Equal("IN (?, ?)", InParamString(2))
    assert.Equal("IN (?, ?, ?)", InParamString(3))
}
