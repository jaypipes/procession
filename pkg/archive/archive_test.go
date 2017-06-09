package archive

import (
    "io/ioutil"
    "testing"

    pb "github.com/jaypipes/procession/proto"
)

func TestArchive(t *testing.T) {
    tmpLogFile, err := ioutil.TempFile("", "archive.testlog")
    if err != nil {
        t.Fatalf("Unable to create temporary log file: %v", err)
    }
    tmpLogPath := tmpLogFile.Name()
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
    err = archiver.Archive(rec)
    if err != nil {
        t.Fatalf("Expected nil error when archiving but got %v", err)
    }
}

