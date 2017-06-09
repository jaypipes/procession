package archive

import (
    "io/ioutil"
    "os"
    "testing"

    "github.com/golang/protobuf/proto"

    pb "github.com/jaypipes/procession/proto"
)

func TestArchive(t *testing.T) {
    tmpLogFile, err := ioutil.TempFile("", "archive.log-")
    if err != nil {
        t.Fatalf("Unable to create temporary log file: %v", err)
    }
    tmpLogPath := tmpLogFile.Name()
    defer os.Remove(tmpLogPath)

    cfg := &Config{
        LogFilePath: tmpLogPath,
    }
    archiver, err := New(cfg)
    if err != nil {
        t.Fatalf("Expected nil error when creating archiver but got %v", err)
    }
    afterAttrs := make([]*pb.ArchiveAttribute, 0)
    afterAttrs = append(afterAttrs, &pb.ArchiveAttribute{
        Key: "key", Value: &pb.ArchiveAttribute_ValInt{789},
    })
    rec := &pb.ArchiveRecord{
        Action: pb.ArchiveAction_CREATE,
        Timestamp: 12345,
        After: &pb.After{
            Attributes: afterAttrs,
        },
    }
    trw := &archiver.Stats.TotalRecordsWritten
    tbw := &archiver.Stats.TotalBytesWritten
    tc := &archiver.Stats.TotalCreate

    if *trw != 0 {
        t.Fatalf("Expected 0 records written, got %d", *trw)
    }
    if *tbw != 0 {
        t.Fatalf("Expected 0 bytes written, got %d", *tbw)
    }
    if *tc != 0 {
        t.Fatalf("Expected 0 create records, got %d", *tc)
    }

    err = archiver.Archive(rec)
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

    rRec := &pb.ArchiveRecord{}
    data, err := ioutil.ReadFile(tmpLogPath)
    if err != nil {
        t.Fatalf("Expected nil error when reading log, but got %v", err)
    }
    err = proto.Unmarshal(data, rRec)
    if err != nil {
        t.Fatalf("Expected nil error when unmarshalling log, but got %v", err)
    }

    if ! proto.Equal(rec, rRec) {
        t.Fatalf("Expected equal messages, but got %v vs. %v", rec, rRec)
    }
}
