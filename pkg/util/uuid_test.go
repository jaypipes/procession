package util

import (
    "testing"
)

func TestOrderedUuid(t *testing.T) {
    uuids := []string{
        OrderedUuid(),
        OrderedUuid(),
        OrderedUuid(),
        OrderedUuid(),
    }

    for x := 1; x < 4; x++ {
        if uuids[x - 1] > uuids[x] {
            t.Errorf("UUID %v should be less than UUID %v",
                     uuids[x - 1], uuids[x])
        }
    }
}
