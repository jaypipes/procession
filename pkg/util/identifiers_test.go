package util

import (
    "testing"
)

func TestUuid1OrderedChar32(t *testing.T) {
    uuids := []string{
        Uuid1OrderedChar32(),
        Uuid1OrderedChar32(),
        Uuid1OrderedChar32(),
        Uuid1OrderedChar32(),
    }

    for x := 1; x < 4; x++ {
        if uuids[x - 1] > uuids[x] {
            t.Errorf("UUID %v should be less than UUID %v",
                     uuids[x - 1], uuids[x])
        }
    }
}

func TestUuid4Char32(t *testing.T) {
    u32 := Uuid4Char32()
    if len(u32) != 32 {
        t.Errorf("Expected %s top be 32 characters but got %d", u32, len(u32))
    }
}

func TestUuidFormatDb(t *testing.T) {
    tests := map[string]string{
        "": "",
        "  ": "",
        "00000000-0000-0000-0000-000000000000": "00000000000000000000000000000000",
        "00000000-0000-0000-0000-000000000000  ": "00000000000000000000000000000000",
        "  00000000-0000-0000-0000-000000000000": "00000000000000000000000000000000",
        "  00000000-0000-0000-0000-000000000000  ": "00000000000000000000000000000000",
        "00000000000000000000000000000000": "00000000000000000000000000000000",
        "d401cf51-31ab-4425-818a-9f25ea1706f5": "d401cf5131ab4425818a9f25ea1706f5",
        "d401cf5131ab4425818a9f25ea1706f5": "d401cf5131ab4425818a9f25ea1706f5",
        "D401CF51-31AB-4425-818A-9F25EA1706F5": "d401cf5131ab4425818a9f25ea1706f5",
        "D401CF5131AB4425818A9F25EA1706F5": "d401cf5131ab4425818a9f25ea1706f5",
    }
    for subject, expect := range tests {
        got := UuidFormatDb(subject)
        if got != expect {
            t.Errorf("For %s expected %v but got %v", subject, expect, got)
        }
    }
}

func TestIsUuidLike(t *testing.T) {
    tests := map[string]bool{
        "": false,
        "  ": false,
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

func TestIsEmailLike(t *testing.T) {
    tests := map[string]bool{
        "": false,
        "  ": false,
        "my space@myspace.com": false,
        "my\nspace@myspace.com": false,
        "root@localhost": true,
        "jaypipes@gmail.com": true,
        "supercalifragilsticexpealadocious@disney.com": true,
    }
    for subject, expect := range tests {
        if IsEmailLike(subject) != expect {
            t.Errorf("For %s expected %v but got %v", subject, expect, !expect)
        }
    }
}
