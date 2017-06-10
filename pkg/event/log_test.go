package event

import (
    "bytes"
    "io/ioutil"
    "os"
    "testing"

    "github.com/golang/protobuf/proto"

    pb "github.com/jaypipes/procession/proto"
)

func TestLog(t *testing.T) {
    tmpLogFile, err := ioutil.TempFile("", "archive.log-")
    if err != nil {
        t.Fatalf("Unable to create temporary log file: %v", err)
    }
    tmpLogPath := tmpLogFile.Name()
    defer os.Remove(tmpLogPath)

    cfg := &Config{
        LogFilePath: tmpLogPath,
    }
    evlog, err := NewLogger(cfg)
    if err != nil {
        t.Fatalf("Expected nil error when creating evlog but got %v", err)
    }
    trw := &evlog.Stats.TotalEventsWritten
    tbw := &evlog.Stats.TotalBytesWritten
    tc := &evlog.Stats.TotalCreate

    if *trw != 0 {
        t.Fatalf("Expected 0 records written, got %d", *trw)
    }
    if *tbw != 0 {
        t.Fatalf("Expected 0 bytes written, got %d", *tbw)
    }
    if *tc != 0 {
        t.Fatalf("Expected 0 create records, got %d", *tc)
    }

    etype := pb.EventType_CREATE
    otype := pb.ObjectType_ORGANIZATION
    ouuid := "org1"
    dn := "my org"
    slug := "my-org"

    before := &pb.Organization{
        Uuid: ouuid,
        DisplayName: dn,
        Slug: slug,
        Generation: 1,
    }
    beforeb, err := proto.Marshal(before)
    if err != nil {
        t.Fatalf("Expected nil error when serializing before but got %v", err)
    }

    err = evlog.Write(etype, otype, ouuid, beforeb, nil)
    if err != nil {
        t.Fatalf("Expected nil error when archiving but got %v", err)
    }

    if *trw <= 0 {
        t.Fatalf("Expected >0 records written, got 0")
    }
    if *tbw <= 0 {
        t.Fatalf("Expected >0 bytes written, got 0")
    }
    if *tc != 1 {
        t.Fatalf("Expected 1 create records, got %d", tc)
    }

    ev := &pb.Event{}
    data, err := ioutil.ReadFile(tmpLogPath)
    if err != nil {
        t.Fatalf("Expected nil error when reading log, but got %v", err)
    }
    err = proto.Unmarshal(data, ev)
    if err != nil {
        t.Fatalf("Expected nil error when unmarshalling log, but got %v", err)
    }

    expect := &pb.Event{
        Type: etype,
        ObjectType: otype,
        ObjectUuid: ouuid,
        Before: beforeb,
        After: nil,
    }

    if expect.Type != ev.Type {
        t.Fatalf("Expected equal event types, but got %v vs. %v",
                 expect.Type, ev.Type)
    }
    if expect.ObjectType != ev.ObjectType {
        t.Fatalf("Expected equal objecttypes, but got %v vs. %v",
                 expect.ObjectType, ev.ObjectType)
    }
    if expect.ObjectUuid != ev.ObjectUuid {
        t.Fatalf("Expected equal object UUIDs, but got %v vs. %v",
                 expect.ObjectUuid, ev.ObjectUuid)
    }
    if ! bytes.Equal(expect.Before, ev.Before) {
        t.Fatalf("Expected equal Before values, but got %v vs. %v",
                 expect.Before, ev.Before)
    }
    if ! bytes.Equal(expect.After, ev.After) {
        t.Fatalf("Expected equal After values, but got %v vs. %v",
                 expect.After, ev.After)
    }
}
