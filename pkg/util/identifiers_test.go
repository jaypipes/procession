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

func TestIsUUidLike(t *testing.T) {
    tests := map[string]bool{
        "00000000-0000-0000-0000-000000000000": true,
        "00000000-0000-0000-0000-000000000000  ": true,
        "  00000000-0000-0000-0000-000000000000": true,
        "  00000000-0000-0000-0000-000000000000  ": true,
        "00000000000000000000000000000000": true,
        "d401cf51-31ab-4425-818a-9f25ea1706f5": true,
        "d401cf5131ab4425818a9f25ea1706f5": true,
        "D401CF51-31AB-4425-818A-9F25EA1706F5": true,
        "D401CF5131AB4425818A9F25EA1706F5": true,
        "0000000000000000000000000000000": false,
        "00000000-0000-0000-0000-00000000000": false,
        "00000000-0000-0000-0000-000000000000-": false,
        "quickbrownfoxjumpedoverthebrowndogno": false,
        "quick-brownf-oxjump-edov-erthebrowndogno": false,
    }
    for subject, expect := range tests {
        if IsUuidLike(subject) != expect {
            t.Errorf("For %s expected %v but got %v", subject, expect, !expect)
        }
    }
}
